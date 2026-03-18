from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp_type = serializers.ChoiceField(choices=['registration', 'password_reset'], default='registration')


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(min_length=6, max_length=6)
    otp_type = serializers.ChoiceField(choices=['registration', 'password_reset'], default='registration')


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return attrs
