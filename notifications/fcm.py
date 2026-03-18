"""
Firebase Cloud Messaging (FCM) — HTTP v1 API implementation.

The legacy FCM server key API (fcm.googleapis.com/fcm/send) is deprecated as of June 2024.
This module uses the FCM HTTP v1 API authenticated with a service account JSON key.

Setup:
1. In Firebase Console → Project Settings → Service Accounts → Generate new private key
2. Save the JSON file securely on your server
3. Set FCM_SERVICE_ACCOUNT_FILE=/path/to/serviceAccountKey.json in your .env

For multi-device (topic) sends, use send_to_topic().
For single device, use send_to_device().
"""
import json
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger('notifications')


def _get_access_token() -> Optional[str]:
    """
    Obtain a short-lived OAuth2 access token from the service account credentials.
    Uses google-auth library if available; falls back gracefully.
    """
    service_account_file = getattr(settings, 'FCM_SERVICE_ACCOUNT_FILE', '')
    if not service_account_file:
        logger.error("FCM_SERVICE_ACCOUNT_FILE not set in settings.")
        return None

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GoogleRequest

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/firebase.messaging'],
        )
        credentials.refresh(GoogleRequest())
        return credentials.token
    except ImportError:
        logger.error(
            "google-auth not installed. Run: pip install google-auth"
        )
        return None
    except Exception as e:
        logger.error(f"FCM access token error: {e}")
        return None


def _get_project_id() -> Optional[str]:
    service_account_file = getattr(settings, 'FCM_SERVICE_ACCOUNT_FILE', '')
    if not service_account_file:
        return getattr(settings, 'FCM_PROJECT_ID', None)
    try:
        with open(service_account_file) as f:
            return json.load(f).get('project_id')
    except Exception:
        return getattr(settings, 'FCM_PROJECT_ID', None)


def send_to_device(
    fcm_token: str,
    title: str,
    body: str,
    data: dict = None,
    image_url: str = None,
) -> tuple[bool, str]:
    """
    Send a push notification to a single device via FCM HTTP v1 API.

    Args:
        fcm_token: Device registration token from the mobile app
        title: Notification title
        body: Notification body text
        data: Optional dict of custom key-value pairs (delivered even when app is backgrounded)
        image_url: Optional URL of image to display in notification

    Returns:
        (success: bool, error_message: str)
    """
    import requests

    if not fcm_token:
        return False, "Empty FCM token."

    access_token = _get_access_token()
    if not access_token:
        return False, "Could not obtain FCM access token."

    project_id = _get_project_id()
    if not project_id:
        return False, "FCM project_id not configured."

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    notification_payload = {
        "title": title,
        "body": body,
    }
    if image_url:
        notification_payload["image"] = image_url

    message = {
        "token": fcm_token,
        "notification": notification_payload,
        "android": {
            "notification": {
                "sound": "default",
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
            }
        },
        "apns": {
            "payload": {
                "aps": {
                    "sound": "default",
                    "badge": 1,
                }
            }
        },
    }

    if data:
        # FCM data payload — all values must be strings
        message["data"] = {k: str(v) for k, v in data.items()}

    try:
        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"message": message},
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            msg_name = result.get("name", "")
            logger.info(f"FCM push sent: {msg_name} → token ...{fcm_token[-10:]}")
            return True, ""

        # Handle known FCM errors
        error_body = response.json()
        error_status = error_body.get("error", {}).get("status", "")
        error_msg = error_body.get("error", {}).get("message", response.text)

        if error_status == "UNREGISTERED":
            # Token is no longer valid — clear it from our DB
            logger.warning(f"FCM token unregistered: ...{fcm_token[-10:]}")
            _clear_stale_token(fcm_token)
            return False, "FCM token unregistered (cleared from DB)."

        if error_status == "INVALID_ARGUMENT":
            logger.warning(f"FCM invalid token: ...{fcm_token[-10:]}")
            return False, f"FCM invalid argument: {error_msg}"

        logger.error(f"FCM error {response.status_code}: {error_msg}")
        return False, error_msg

    except Exception as e:
        logger.error(f"FCM request exception: {e}")
        return False, str(e)


def send_to_topic(
    topic: str,
    title: str,
    body: str,
    data: dict = None,
) -> tuple[bool, str]:
    """
    Send a push notification to all devices subscribed to a topic.
    Topics are useful for broadcast notifications (e.g. 'all_users', 'promo').
    """
    import requests

    access_token = _get_access_token()
    if not access_token:
        return False, "Could not obtain FCM access token."

    project_id = _get_project_id()
    if not project_id:
        return False, "FCM project_id not configured."

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    message = {
        "topic": topic,
        "notification": {"title": title, "body": body},
    }
    if data:
        message["data"] = {k: str(v) for k, v in data.items()}

    try:
        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"message": message},
            timeout=10,
        )
        if response.status_code == 200:
            logger.info(f"FCM topic '{topic}' push sent.")
            return True, ""
        error_msg = response.json().get("error", {}).get("message", response.text)
        logger.error(f"FCM topic send error: {error_msg}")
        return False, error_msg
    except Exception as e:
        logger.error(f"FCM topic request exception: {e}")
        return False, str(e)


def send_multicast(
    fcm_tokens: list,
    title: str,
    body: str,
    data: dict = None,
) -> dict:
    """
    Send to multiple devices (up to 500 at a time).
    Returns {'success': int, 'failure': int, 'errors': list}
    """
    results = {'success': 0, 'failure': 0, 'errors': []}
    for token in fcm_tokens:
        ok, err = send_to_device(token, title, body, data)
        if ok:
            results['success'] += 1
        else:
            results['failure'] += 1
            results['errors'].append({'token': token[-10:], 'error': err})
    return results


def _clear_stale_token(fcm_token: str):
    """Remove an unregistered FCM token from all users."""
    try:
        from accounts.models import User
        User.objects.filter(fcm_token=fcm_token).update(fcm_token='')
    except Exception as e:
        logger.error(f"Failed to clear stale FCM token: {e}")
