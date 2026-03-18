"""
Notification service — Email, SMS (Fast2SMS), WhatsApp (Gupshup/AiSensy), Push (FCM v1).
All external calls isolated here. Views and tasks call only this module.
"""
import json
import logging
import requests
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from .models import Notification, NotificationTemplate

logger = logging.getLogger('notifications')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render(template_str: str, context: dict) -> str:
    """
    FIX: Use Django's Template engine instead of manual str.replace.
    This provides proper HTML escaping and graceful handling of missing keys
    (missing variables render as empty string by default in Django templates).
    Note: template variables use {{ var }} in Django Template syntax.
    For backwards compat with existing templates using {var}, we first
    convert {var} → {{ var }}.
    """
    from django.template import Template, Context
    # Convert simple {key} placeholders to Django {{ key }} template syntax
    for k in context:
        template_str = template_str.replace(f'{{{k}}}', f'{{{{ {k} }}}}')
    try:
        return Template(template_str).render(Context(context, autoescape=False))
    except Exception:
        # Fallback: plain replacement so notifications never silently fail
        result = template_str
        for k, v in context.items():
            result = result.replace(f'{{{{ {k} }}}}', str(v))
        return result


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith('+91'):
        phone = phone[3:]
    elif phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    return phone.lstrip('0')


# ── Email ─────────────────────────────────────────────────────────────────────

def _send_email(user, subject: str, body: str) -> tuple[bool, str]:
    if not user.email:
        return False, 'User has no email address.'
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@cakemallow.com'),
            to=[user.email],
        )
        if '<' in body and '>' in body:
            msg.attach_alternative(body, 'text/html')
        msg.send(fail_silently=False)
        return True, ''
    except Exception as e:
        return False, str(e)


# ── SMS — Fast2SMS ─────────────────────────────────────────────────────────────

def _send_fast2sms(phone: str, message: str) -> tuple[bool, str]:
    api_key = getattr(django_settings, 'FAST2SMS_API_KEY', '')
    if not api_key:
        return False, 'FAST2SMS_API_KEY not configured.'
    phone = _normalize_phone(phone)
    try:
        response = requests.post(
            url='https://www.fast2sms.com/dev/bulkV2',
            headers={'authorization': api_key, 'Content-Type': 'application/json'},
            json={'route': 'q', 'message': message, 'language': 'english', 'numbers': phone},
            timeout=10,
        )
        result = response.json()
        if result.get('return') is True:
            return True, ''
        return False, str(result.get('message', result))
    except Exception as e:
        return False, str(e)


# ── WhatsApp — Gupshup / AiSensy ─────────────────────────────────────────────

def _send_whatsapp_gupshup(phone: str, message: str) -> tuple[bool, str]:
    api_key = getattr(django_settings, 'GUPSHUP_API_KEY', '')
    source = getattr(django_settings, 'GUPSHUP_SOURCE', '')
    if not api_key or not source:
        return False, 'Gupshup API_KEY/SOURCE not configured.'
    phone = _normalize_phone(phone)
    try:
        response = requests.post(
            url='https://api.gupshup.io/sm/api/v1/msg',
            headers={'apikey': api_key, 'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'channel': 'whatsapp',
                'source': source,
                'destination': f'91{phone}',
                # FIX: use json.dumps to safely encode the message.
                # Previously an f-string was used, which breaks if message contains
                # double quotes (e.g. cake message: He said "Happy Birthday!")
                'message': json.dumps({'type': 'text', 'text': message}),
                'src.name': 'Cakemallow',
            },
            timeout=10,
        )
        result = response.json()
        if result.get('status') == 'submitted':
            return True, ''
        return False, str(result)
    except Exception as e:
        return False, str(e)


def _send_whatsapp_aisensy(phone: str, message: str) -> tuple[bool, str]:
    api_key = getattr(django_settings, 'AISENSY_API_KEY', '')
    if not api_key:
        return False, 'AISENSY_API_KEY not configured.'
    phone = _normalize_phone(phone)
    try:
        response = requests.post(
            url='https://backend.aisensy.com/campaign/t1/api/v2',
            headers={'Content-Type': 'application/json'},
            json={
                'apiKey': api_key,
                'campaignName': 'cakemallow_notification',
                'destination': f'91{phone}',
                'userName': 'Cakemallow',
                'templateParams': [message],
                'media': {},
            },
            timeout=10,
        )
        if response.status_code == 200:
            return True, ''
        return False, response.text
    except Exception as e:
        return False, str(e)


def _send_whatsapp(phone: str, message: str) -> tuple[bool, str]:
    provider = getattr(django_settings, 'WHATSAPP_PROVIDER', '').lower()
    if provider == 'gupshup':
        return _send_whatsapp_gupshup(phone, message)
    if provider == 'aisensy':
        return _send_whatsapp_aisensy(phone, message)
    return False, f"WHATSAPP_PROVIDER '{provider}' not supported. Set gupshup or aisensy."


# ── Push — FCM v1 API ─────────────────────────────────────────────────────────

def _send_push(user, title: str, body: str, data: dict = None) -> tuple[bool, str]:
    """
    Send FCM push via the HTTP v1 API (uses service account, not deprecated server key).
    Requires: FCM_SERVICE_ACCOUNT_FILE set in settings.
    Requires: pip install google-auth
    """
    fcm_token = getattr(user, 'fcm_token', '').strip()
    if not fcm_token:
        return False, 'No FCM token stored for user.'

    from notifications.fcm import send_to_device
    return send_to_device(fcm_token, title, body, data=data)


# ── Main dispatcher ───────────────────────────────────────────────────────────

def send_notification(user, event: str, context: dict = None):
    """
    Dispatch notifications across all active channels for a given event.
    Silently skips channels with no template body configured.
    """
    context = context or {}

    try:
        template = NotificationTemplate.objects.get(event=event, is_active=True)
    except NotificationTemplate.DoesNotExist:
        logger.debug(f"No active template for event '{event}' — skipping.")
        return

    phone = getattr(user, 'phone', None)

    # ── Email ────────────────────────────────────────────────────────────────
    if template.email_body and user.email:
        subject = _render(template.email_subject, context)
        body = _render(template.email_body, context)
        notif = Notification.objects.create(user=user, channel='email', subject=subject, message=body)
        ok, err = _send_email(user, subject, body)
        _save(notif, ok, err)
        if not ok:
            logger.error(f"Email failed user={user.id} event={event}: {err}")

    # ── SMS ──────────────────────────────────────────────────────────────────
    if template.sms_body and phone:
        body = _render(template.sms_body, context)
        notif = Notification.objects.create(user=user, channel='sms', message=body)
        ok, err = _send_fast2sms(phone, body)
        _save(notif, ok, err)
        if not ok:
            logger.error(f"SMS failed user={user.id} event={event}: {err}")

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    if template.whatsapp_body and phone:
        body = _render(template.whatsapp_body, context)
        notif = Notification.objects.create(user=user, channel='whatsapp', message=body)
        ok, err = _send_whatsapp(phone, body)
        _save(notif, ok, err)
        if not ok:
            logger.warning(f"WhatsApp failed user={user.id} event={event}: {err}")

    # ── Push (FCM v1) ─────────────────────────────────────────────────────────
    if template.push_title and template.push_body:
        title = _render(template.push_title, context)
        body = _render(template.push_body, context)
        notif = Notification.objects.create(user=user, channel='push', subject=title, message=body)
        ok, err = _send_push(user, title, body, data=context)
        _save(notif, ok, err)
        if not ok:
            logger.warning(f"Push failed user={user.id} event={event}: {err}")


def _save(notif: Notification, ok: bool, err: str):
    notif.status = 'sent' if ok else 'failed'
    notif.error = '' if ok else err
    if ok:
        notif.sent_at = timezone.now()
    notif.save()
