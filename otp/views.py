"""
OTP views — send, verify, registration activation, password reset.
Throttled to prevent SMS flooding and brute-force OTP guessing.
"""
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.throttles import OTPRateThrottle
from .models import OTPCode
from .serializers import SendOTPSerializer, VerifyOTPSerializer, ResetPasswordSerializer
from .services import send_otp_sms

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def send_otp(request):
    """
    POST /api/otp/send/
    { phone, otp_type: 'registration'|'password_reset' }
    Rate-limited: 10/hour per IP.
    """
    serializer = SendOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone    = serializer.validated_data['phone']
    otp_type = serializer.validated_data['otp_type']

    if otp_type == 'password_reset':
        if not User.objects.filter(phone=phone).exists():
            return Response(
                {'error': 'No account found with this phone number.'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Invalidate all previous OTPs for this phone+type
    OTPCode.objects.filter(phone=phone, otp_type=otp_type, is_used=False).update(is_used=True)

    otp = OTPCode.objects.create(phone=phone, otp_type=otp_type)
    purpose = 'registration' if otp_type == 'registration' else 'password reset'
    success = send_otp_sms(phone, otp.code, purpose)

    if not success:
        return Response(
            {'error': 'Failed to send OTP. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    response_data = {
        'message': f'OTP sent to {phone[-4:].rjust(len(phone), "*")}',
        'expires_in_minutes': 10,
    }

    # Expose OTP only in DEBUG mode — NEVER in production
    if settings.DEBUG:
        response_data['dev_otp'] = otp.code

    return Response(response_data)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def verify_otp(request):
    """
    POST /api/otp/verify/
    { phone, code, otp_type }
    Returns { valid: true } — does NOT issue tokens.
    """
    serializer = VerifyOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone    = serializer.validated_data['phone']
    code     = serializer.validated_data['code']
    otp_type = serializer.validated_data['otp_type']

    try:
        otp = OTPCode.objects.filter(
            phone=phone, code=code, otp_type=otp_type, is_used=False
        ).latest('created_at')
    except OTPCode.DoesNotExist:
        return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

    if not otp.is_valid():
        return Response(
            {'error': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({'valid': True, 'message': 'OTP verified successfully.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def verify_registration_otp(request):
    """
    POST /api/otp/verify-registration/
    { phone, code }
    Activates account + issues JWT tokens.
    """
    phone = request.data.get('phone', '').strip()
    code  = request.data.get('code', '').strip()

    if not phone or not code:
        return Response(
            {'error': 'Phone and code are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        otp = OTPCode.objects.filter(
            phone=phone, code=code, otp_type='registration', is_used=False
        ).latest('created_at')
    except OTPCode.DoesNotExist:
        return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

    if not otp.is_valid():
        return Response(
            {'error': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(phone=phone, is_active=False)
    except User.DoesNotExist:
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {'error': 'No account found for this phone.'},
                status=status.HTTP_404_NOT_FOUND
            )

    user.is_active = True
    user.save()
    otp.is_used = True
    otp.save()

    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Phone verified! Account activated.',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'phone': user.phone,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def reset_password(request):
    """
    POST /api/otp/reset-password/
    { phone, code, new_password, new_password2 }
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone        = serializer.validated_data['phone']
    code         = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    try:
        otp = OTPCode.objects.filter(
            phone=phone, code=code, otp_type='password_reset', is_used=False
        ).latest('created_at')
    except OTPCode.DoesNotExist:
        return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

    if not otp.is_valid():
        return Response(
            {'error': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response(
            {'error': 'No account found with this phone number.'},
            status=status.HTTP_404_NOT_FOUND
        )

    user.set_password(new_password)
    user.save()
    otp.is_used = True
    otp.save()

    # Invalidate any remaining unused OTPs for this phone
    OTPCode.objects.filter(phone=phone, otp_type='password_reset', is_used=False).update(is_used=True)

    return Response({'message': 'Password reset successfully. Please sign in with your new password.'})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def resend_otp(request):
    """POST /api/otp/resend/ — re-send OTP, same throttle as send."""
    return send_otp(request)
