"""
OTP sending service.
Uses Fast2SMS if API key is set, else prints to console (dev mode).
Fast2SMS docs: https://docs.fast2sms.com
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_otp_sms(phone: str, otp_code: str, purpose: str = "verification") -> bool:
    """
    Send OTP via SMS using Fast2SMS. Returns True on success.
    Falls back to console print if Fast2SMS not configured.

    phone: Indian mobile number (10 digits or with +91 prefix)
    """
    # Normalize phone — Fast2SMS expects 10-digit Indian number (no country code)
    phone = phone.strip()
    if phone.startswith('+91'):
        phone = phone[3:]
    elif phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    phone = phone.lstrip('0')

    message = (
        f"Your Cakemallow {purpose} OTP is: {otp_code}. "
        f"Valid for 10 minutes. Do not share with anyone."
    )

    api_key = getattr(settings, 'FAST2SMS_API_KEY', '')

    if api_key:
        try:
            response = requests.post(
                url='https://www.fast2sms.com/dev/bulkV2',
                headers={
                    'authorization': api_key,
                    'Content-Type': 'application/json',
                },
                json={
                    'route': 'otp',           # OTP route for transactional messages
                    'variables_values': otp_code,
                    'numbers': phone,
                },
                timeout=10,
            )
            result = response.json()
            if result.get('return') is True:
                logger.info(f"OTP sent via Fast2SMS to {phone}")
                return True
            else:
                logger.error(f"Fast2SMS error: {result.get('message', result)}")
                # Fall through to console
        except Exception as e:
            logger.error(f"Fast2SMS request failed: {e}")
            # Fall through to console

    # Dev fallback — print to console
    print(f"\n{'='*50}")
    print(f"[OTP CONSOLE] Phone: {phone}")
    print(f"[OTP CONSOLE] Code: {otp_code}")
    print(f"[OTP CONSOLE] Purpose: {purpose}")
    print(f"{'='*50}\n")
    return True