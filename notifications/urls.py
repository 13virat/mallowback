from django.urls import path
from .views import (
    my_notifications,
    all_notifications,
    notification_stats,
    list_templates,
    create_template,
    update_template,
    send_broadcast,
    list_campaigns,
    create_campaign,
    campaign_detail,
    send_campaign_now,
    run_birthday_campaigns_now,
)

urlpatterns = [
    # Customer
    path('', my_notifications, name='my-notifications'),

    # Admin — notification log
    path('all/',              all_notifications,  name='all-notifications'),
    path('stats/',            notification_stats, name='notification-stats'),

    # Admin — templates
    path('templates/',        list_templates,     name='notification-templates'),
    path('templates/create/', create_template,    name='notification-template-create'),
    path('templates/<int:pk>/', update_template,  name='notification-template-update'),

    # Admin — broadcast
    path('broadcast/',        send_broadcast,     name='notification-broadcast'),

    # Admin — campaigns
    path('campaigns/',                    list_campaigns,            name='campaign-list'),
    path('campaigns/create/',             create_campaign,           name='campaign-create'),
    path('campaigns/birthday/run/',       run_birthday_campaigns_now, name='campaign-birthday-run'),
    path('campaigns/<int:pk>/',           campaign_detail,           name='campaign-detail'),
    path('campaigns/<int:pk>/send/',      send_campaign_now,         name='campaign-send'),
]