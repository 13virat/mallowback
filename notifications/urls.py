from django.urls import path
from .views import (
    my_notifications,
    all_notifications,
    notification_stats,
    list_templates,
    create_template,
    update_template,
    send_broadcast,
)

urlpatterns = [
    # Customer
    path('', my_notifications, name='my-notifications'),

    # Admin
    path('all/',             all_notifications,  name='all-notifications'),
    path('stats/',           notification_stats, name='notification-stats'),
    path('templates/',       list_templates,     name='notification-templates'),
    path('templates/create/', create_template,   name='notification-template-create'),
    path('templates/<int:pk>/', update_template, name='notification-template-update'),
    path('broadcast/',       send_broadcast,     name='notification-broadcast'),
]