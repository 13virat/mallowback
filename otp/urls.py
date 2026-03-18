from django.urls import path
from .views import send_otp, verify_otp, verify_registration_otp, reset_password, resend_otp

urlpatterns = [
    path('send/',                  send_otp,                  name='otp-send'),
    path('verify/',                verify_otp,                name='otp-verify'),
    path('verify-registration/',   verify_registration_otp,   name='otp-verify-registration'),
    path('reset-password/',        reset_password,            name='otp-reset-password'),
    path('resend/',                resend_otp,                name='otp-resend'),
]
