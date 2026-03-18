from django.urls import path
from .views import (
    address_list, address_detail, create_order, user_orders,
    order_detail, cancel_order, admin_update_order_status,
)

urlpatterns = [
    path('addresses/', address_list, name='address-list'),
    path('addresses/<int:pk>/', address_detail, name='address-detail'),
    path('create/', create_order, name='order-create'),
    path('my/', user_orders, name='order-list'),
    path('<int:pk>/', order_detail, name='order-detail'),
    path('<int:pk>/cancel/', cancel_order, name='order-cancel'),
    path('<int:pk>/admin-status/', admin_update_order_status, name='order-admin-status'),
]
