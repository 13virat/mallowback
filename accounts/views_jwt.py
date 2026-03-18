"""
Custom JWT login view — applies login rate throttle.
"""
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import ScopedRateThrottle
from .serializers import CustomTokenObtainPairSerializer


class LoginThrottle(ScopedRateThrottle):
    scope = 'login'


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Rate-limited login with custom JWT claims (email, phone, is_staff in token payload).
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]
