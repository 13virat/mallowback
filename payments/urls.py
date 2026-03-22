from django.urls import path
from .views import (
    initiate_payment, verify_payment, cod_payment, razorpay_webhook,
    initiate_advance_payment, verify_advance_payment, mark_remaining_paid,
)

urlpatterns = [
    # Normal order payments
    path('initiate/<int:order_id>/',         initiate_payment,       name='payment-initiate'),
    path('verify/',                           verify_payment,         name='payment-verify'),
    path('cod/<int:order_id>/',              cod_payment,            name='payment-cod'),
    path('webhook/razorpay/',                razorpay_webhook,       name='payment-webhook'),

    # Custom cake advance payments
    path('advance/<int:order_id>/',          initiate_advance_payment, name='payment-advance-initiate'),
    path('advance/verify/',                  verify_advance_payment,   name='payment-advance-verify'),
    path('advance/<int:order_id>/mark-paid/', mark_remaining_paid,     name='payment-advance-mark-paid'),
]