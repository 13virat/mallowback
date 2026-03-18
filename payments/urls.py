from django.urls import path
from .views import initiate_payment, verify_payment, cod_payment, razorpay_webhook

urlpatterns = [
    path('initiate/<int:order_id>/', initiate_payment, name='payment-initiate'),
    path('verify/', verify_payment, name='payment-verify'),
    path('cod/<int:order_id>/', cod_payment, name='payment-cod'),
    path('webhook/razorpay/', razorpay_webhook, name='payment-webhook'),
]
