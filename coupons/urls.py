from django.urls import path
from .views import apply_coupon, available_coupons

urlpatterns = [
    path('apply/', apply_coupon, name='coupon-apply'),
    path('', available_coupons, name='coupon-list'),
]
