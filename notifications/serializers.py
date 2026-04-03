from rest_framework import serializers
from .models import Notification, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'channel', 'subject', 'message', 'status', 'created_at', 'sent_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'


class CampaignSerializer(serializers.ModelSerializer):
    status_display        = serializers.CharField(source='get_status_display', read_only=True)
    campaign_type_display = serializers.CharField(source='get_campaign_type_display', read_only=True)
    channel_display       = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        from .models import Campaign
        model = Campaign
        fields = [
            'id', 'name', 'campaign_type', 'campaign_type_display',
            'channel', 'channel_display', 'status', 'status_display',
            'subject', 'email_body', 'whatsapp_msg', 'push_title', 'push_body',
            'include_coupon', 'coupon_discount', 'coupon_type',
            'coupon_valid_days', 'coupon_prefix',
            'total_recipients', 'sent_count', 'failed_count',
            'created_at', 'sent_at',
        ]
        read_only_fields = ['status', 'total_recipients', 'sent_count', 'failed_count', 'created_at', 'sent_at']