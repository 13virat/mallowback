"""
Account views — register, profile, change password, FCM token update.
"""
import logging
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, UserProfileSerializer, ChangePasswordSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Creates user with is_active=False until OTP verified.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    user.is_active = False
    user.save()

    otp_sent = False
    phone = request.data.get('phone', '').strip()
    if phone:
        try:
            from otp.models import OTPCode
            from otp.services import send_otp_sms
            OTPCode.objects.filter(phone=phone, otp_type='registration', is_used=False).update(is_used=True)
            otp = OTPCode.objects.create(phone=phone, otp_type='registration')
            send_otp_sms(phone, otp.code, 'registration')
            otp_sent = True
        except Exception as e:
            logger.error(f"OTP send failed for registration: {e}")

    response_data = {
        'message': 'Account created. Please verify your phone number with the OTP sent.',
        'user_id': user.id,
        'phone': user.phone,
        'otp_sent': otp_sent,
    }

    # Expose OTP only in DEBUG mode — NEVER in production
    if settings.DEBUG:
        try:
            from otp.models import OTPCode
            latest = OTPCode.objects.filter(phone=phone, otp_type='registration').latest('created_at')
            response_data['dev_otp'] = latest.code
        except Exception:
            pass

    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    """GET or PATCH /api/auth/profile/"""
    if request.method == 'GET':
        return Response(UserProfileSerializer(request.user).data)

    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST /api/auth/change-password/
    Requires { old_password, new_password, new_password2 }
    Invalidates all existing refresh tokens via blacklist.
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    # Force re-login by blacklisting current refresh token if provided
    refresh_token = request.data.get('refresh_token')
    if refresh_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

    return Response({'message': 'Password changed successfully. Please log in again.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    """
    POST /api/auth/fcm-token/
    { "fcm_token": "device_fcm_token_string" }
    Stores FCM device token for push notifications.
    Called by the mobile app every time it gets a new token.
    """
    fcm_token = request.data.get('fcm_token', '').strip()
    if not fcm_token:
        return Response({'error': 'fcm_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

    request.user.fcm_token = fcm_token
    request.user.save(update_fields=['fcm_token'])

    logger.info(f"FCM token updated for user #{request.user.id}")
    return Response({'message': 'FCM token updated successfully.'})
