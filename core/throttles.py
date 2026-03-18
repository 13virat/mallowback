"""
Custom rate limiters for sensitive endpoints.
"""
from rest_framework.throttling import ScopedRateThrottle, AnonRateThrottle


class PaymentRateThrottle(ScopedRateThrottle):
    """20 payment initiations per hour per user."""
    scope = 'payment'


class OTPRateThrottle(ScopedRateThrottle):
    """10 OTP requests per hour per IP."""
    scope = 'otp'


class LoginRateThrottle(AnonRateThrottle):
    """10 login attempts per minute per IP — brute-force protection."""
    scope = 'login'


class BurstRateThrottle(AnonRateThrottle):
    """Burst protection: 30 requests per minute."""
    scope = 'burst'
    rate = '30/minute'
