from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from .models import Notification, NotificationTemplate
from .serializers import NotificationSerializer, NotificationTemplateSerializer
import logging

logger = logging.getLogger('notifications')


# ── Customer endpoint ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    notifs = Notification.objects.filter(user=request.user)[:50]
    return Response(NotificationSerializer(notifs, many=True).data)


# ── Admin endpoints ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_notifications(request):
    """Admin: all notifications with optional filters."""
    qs = Notification.objects.select_related('user').all()

    channel = request.query_params.get('channel')
    if channel:
        qs = qs.filter(channel=channel)

    notif_status = request.query_params.get('status')
    if notif_status:
        qs = qs.filter(status=notif_status)

    qs = qs[:200]
    data = []
    for n in qs:
        d = NotificationSerializer(n).data
        d['user_email'] = n.user.email
        d['user_name'] = n.user.get_full_name() or n.user.username
        data.append(d)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def notification_stats(request):
    """Admin: summary stats for dashboard."""
    from django.utils import timezone
    from datetime import timedelta

    total   = Notification.objects.count()
    sent    = Notification.objects.filter(status='sent').count()
    failed  = Notification.objects.filter(status='failed').count()
    pending = Notification.objects.filter(status='pending').count()

    # By channel
    by_channel = dict(
        Notification.objects.values('channel')
        .annotate(count=Count('id'))
        .values_list('channel', 'count')
    )

    # Today
    today_start = timezone.now().replace(hour=0, minute=0, second=0)
    today_count = Notification.objects.filter(created_at__gte=today_start).count()

    return Response({
        'total':      total,
        'sent':       sent,
        'failed':     failed,
        'pending':    pending,
        'today':      today_count,
        'by_channel': by_channel,
        'delivery_rate': round((sent / total * 100), 1) if total > 0 else 0,
    })


# ── Template management ───────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_templates(request):
    templates = NotificationTemplate.objects.all().order_by('event')
    return Response(NotificationTemplateSerializer(templates, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_template(request):
    serializer = NotificationTemplateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PATCH', 'GET'])
@permission_classes([IsAdminUser])
def update_template(request, pk):
    try:
        template = NotificationTemplate.objects.get(id=pk)
    except NotificationTemplate.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(NotificationTemplateSerializer(template).data)

    serializer = NotificationTemplateSerializer(template, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# ── Send broadcast notification ───────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_broadcast(request):
    """
    Admin: send a manual notification to all users or specific users.
    Body: { event, user_ids (optional), context (optional) }
    """
    event    = request.data.get('event')
    user_ids = request.data.get('user_ids', [])   # empty = all users
    context  = request.data.get('context', {})

    if not event:
        return Response({'error': 'event is required.'}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    users = User.objects.filter(id__in=user_ids) if user_ids else User.objects.filter(is_active=True)
    count = users.count()

    from notifications.services import send_notification
    sent = 0
    for user in users:
        try:
            send_notification(user, event, context)
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for user #{user.id}: {e}")

    return Response({
        'message': f'Broadcast sent to {sent}/{count} users.',
        'event':   event,
        'sent':    sent,
        'total':   count,
    })

# ── Campaign endpoints ────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_campaigns(request):
    from .models import Campaign
    from .serializers import CampaignSerializer
    campaigns = Campaign.objects.all()
    return Response(CampaignSerializer(campaigns, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_campaign(request):
    from .models import Campaign
    from .serializers import CampaignSerializer
    serializer = CampaignSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminUser])
def campaign_detail(request, pk):
    from .models import Campaign
    from .serializers import CampaignSerializer
    try:
        campaign = Campaign.objects.get(id=pk)
    except Campaign.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return Response(CampaignSerializer(campaign).data)

    serializer = CampaignSerializer(campaign, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_campaign_now(request, pk):
    """Trigger campaign send immediately in background thread."""
    from .models import Campaign
    from .serializers import CampaignSerializer
    from .campaign_services import execute_campaign
    from core.thread_tasks import run_async

    try:
        campaign = Campaign.objects.get(id=pk)
    except Campaign.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if campaign.status == 'sending':
        return Response({'error': 'Campaign is already sending.'}, status=400)

    # Run in background so API returns immediately
    run_async(execute_campaign, campaign.id)

    return Response({
        'message': f'Campaign "{campaign.name}" started sending.',
        'campaign_id': campaign.id,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def run_birthday_campaigns_now(request):
    """Manually trigger birthday campaigns for today (for testing)."""
    from .models import Campaign
    from .campaign_services import execute_campaign
    from core.thread_tasks import run_async
    from datetime import date

    today = date.today()
    birthday_campaigns = Campaign.objects.filter(campaign_type='birthday', status='draft')
    count = birthday_campaigns.count()

    if count == 0:
        return Response({'message': 'No birthday campaigns configured. Create one first.'})

    from django.contrib.auth import get_user_model
    User = get_user_model()
    birthday_users = User.objects.filter(
        is_active=True,
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
    ).count()

    for campaign in birthday_campaigns:
        run_async(execute_campaign, campaign.id)

    return Response({
        'message': f'Triggered {count} birthday campaign(s) for {birthday_users} users with birthday today ({today}).',
        'campaigns': count,
        'birthday_users_today': birthday_users,
    })