"""
campaign_services.py
--------------------
Handles sending campaigns to users.
Cost-effective: Email + Push = free, WhatsApp = ₹0.30-0.70/msg (use sparingly).

Variables available in templates:
  {name}          - user's first name or "there"
  {coupon_code}   - auto-generated personal coupon code
  {discount}      - discount amount/percent
  {valid_days}    - coupon validity in days
  {campaign_name} - campaign name
"""
import logging
import random
import string
from django.utils import timezone

logger = logging.getLogger('notifications')


def _generate_coupon_code(prefix: str, length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=length))
    return f"{prefix.upper()}-{suffix}"


def _render(template: str, context: dict) -> str:
    for k, v in context.items():
        template = template.replace(f'{{{k}}}', str(v))
    return template


def _create_personal_coupon(user, campaign):
    """Create a unique personal coupon for this user for this campaign."""
    from coupons.models import Coupon
    code = _generate_coupon_code(campaign.coupon_prefix)
    while Coupon.objects.filter(code=code).exists():
        code = _generate_coupon_code(campaign.coupon_prefix)

    return Coupon.objects.create(
        code=code,
        coupon_type=campaign.coupon_type,
        discount_value=campaign.coupon_discount,
        min_order_amount=0,
        max_uses=1,
        max_uses_per_user=1,
        valid_from=timezone.now(),
        valid_until=timezone.now() + __import__('datetime').timedelta(days=campaign.coupon_valid_days),
        is_active=True,
        description=f"Personal coupon from {campaign.name} for {user.get_full_name() or user.email}",
    )


def send_campaign_to_user(campaign, user) -> dict:
    """
    Send a campaign to a single user across configured channels.
    Returns { sent: bool, channels: list, coupon_code: str|None }
    """
    from notifications.models import Notification
    from notifications.services import _send_email, _send_whatsapp, _send_push

    coupon_code = None
    if campaign.include_coupon:
        try:
            coupon = _create_personal_coupon(user, campaign)
            coupon_code = coupon.code
        except Exception as e:
            logger.warning(f"Coupon creation failed for user #{user.id}: {e}")

    context = {
        'name':          user.get_full_name() or user.first_name or 'there',
        'email':         user.email,
        'coupon_code':   coupon_code or '',
        'discount':      str(campaign.coupon_discount),
        'valid_days':    str(campaign.coupon_valid_days),
        'campaign_name': campaign.name,
    }

    sent_channels = []

    # ── Email (free) ──────────────────────────────────────────────────────────
    if campaign.channel in ('email', 'both') and campaign.email_body and user.email:
        subject = _render(campaign.subject or campaign.name, context)
        body    = _render(campaign.email_body, context)
        ok, err = _send_email(user, subject, body)
        n = Notification.objects.create(
            user=user, channel='email', subject=subject, message=body,
            status='sent' if ok else 'failed', error='' if ok else err,
        )
        if ok:
            n.sent_at = timezone.now(); n.save()
            sent_channels.append('email')
        else:
            logger.warning(f"Campaign email failed user #{user.id}: {err}")

    # ── WhatsApp (₹0.30-0.70/msg) ─────────────────────────────────────────────
    if campaign.channel in ('whatsapp', 'both') and campaign.whatsapp_msg:
        phone = getattr(user, 'phone', '') or ''
        if phone:
            msg  = _render(campaign.whatsapp_msg, context)
            ok, err = _send_whatsapp(phone, msg)
            n = Notification.objects.create(
                user=user, channel='whatsapp', message=msg,
                status='sent' if ok else 'failed', error='' if ok else err,
            )
            if ok:
                n.sent_at = timezone.now(); n.save()
                sent_channels.append('whatsapp')
            else:
                logger.warning(f"Campaign WhatsApp failed user #{user.id}: {err}")

    # ── Push via FCM (free) ───────────────────────────────────────────────────
    if campaign.channel == 'push' and campaign.push_title:
        title = _render(campaign.push_title, context)
        body  = _render(campaign.push_body or '', context)
        ok, err = _send_push(user, title, body, data={'coupon_code': coupon_code or ''})
        n = Notification.objects.create(
            user=user, channel='push', subject=title, message=body,
            status='sent' if ok else 'failed', error='' if ok else err,
        )
        if ok:
            n.sent_at = timezone.now(); n.save()
            sent_channels.append('push')

    return {'sent': len(sent_channels) > 0, 'channels': sent_channels, 'coupon_code': coupon_code}


def execute_campaign(campaign_id: int):
    """
    Execute a campaign — sends to all targeted users.
    For birthday: only users whose birthday is today.
    For all others: all active non-staff users.
    """
    from notifications.models import Campaign
    from django.contrib.auth import get_user_model
    from datetime import date
    User = get_user_model()

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"Campaign #{campaign_id} not found")
        return

    campaign.status = 'sending'
    campaign.save()

    if campaign.campaign_type == 'birthday':
        today = date.today()
        users = User.objects.filter(
            is_active=True,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
        )
    else:
        users = User.objects.filter(is_active=True, is_staff=False)

    total = users.count()
    sent = failed = 0

    for user in users:
        try:
            result = send_campaign_to_user(campaign, user)
            if result['sent']: sent += 1
            else: failed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Campaign #{campaign_id} failed for user #{user.id}: {e}")

    campaign.status           = 'sent'
    campaign.total_recipients = total
    campaign.sent_count       = sent
    campaign.failed_count     = failed
    campaign.sent_at          = timezone.now()
    campaign.save()
    logger.info(f"Campaign #{campaign_id} done: {sent}/{total} sent")