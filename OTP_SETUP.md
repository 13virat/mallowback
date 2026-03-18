# 📱 OTP Verification & Password Reset — Setup Guide

## New Auth Flows Added

### 1. Registration with Phone OTP
```
User fills form → POST /api/auth/register/
  → account created with is_active=False
  → OTP auto-sent to phone number
  → Frontend shows 6-digit OTP input
  → POST /api/otp/verify-registration/ { phone, code }
  → account activated, JWT tokens returned
  → User is now logged in
```

### 2. Forgot Password via OTP  
```
User clicks "Forgot password?" → enters phone number
  → POST /api/otp/send/ { phone, otp_type: "password_reset" }
  → OTP sent to registered phone
  → User enters 6-digit OTP
  → POST /api/otp/verify/ { phone, code, otp_type: "password_reset" }
  → User sets new password
  → POST /api/otp/reset-password/ { phone, code, new_password, new_password2 }
  → Password updated, redirect to login
```

## New API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/otp/send/` | Send OTP (registration or password_reset) |
| POST | `/api/otp/verify/` | Verify OTP without activating |
| POST | `/api/otp/verify-registration/` | Verify OTP + activate account + get tokens |
| POST | `/api/otp/reset-password/` | Reset password with verified OTP |
| POST | `/api/otp/resend/` | Resend OTP (invalidates old one) |

## Database Migration
```bash
python manage.py makemigrations otp
python manage.py migrate
```

## SMS Provider Setup (Twilio)

Add to `.env`:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

Install Twilio SDK:
```bash
pip install twilio
```

## Development Mode (No SMS Setup Needed)
Without Twilio configured, OTPs print to the **Django console**:
```
==================================================
[OTP CONSOLE] Phone: 9876543210
[OTP CONSOLE] Code: 483921
[OTP CONSOLE] Purpose: registration
==================================================
```

Also, the OTP is returned in the API response as `dev_otp` field and shown
in the frontend UI as an amber banner — remove this in production by
deleting the `dev_otp` lines from `accounts/views.py` and `otp/views.py`.

## OTP Model Details
- OTPs expire in **10 minutes**
- Each new OTP invalidates previous ones for same phone + type
- Used OTPs cannot be reused (`is_used` flag)
- Viewable in Django admin at `/admin/otp/otpcode/`
