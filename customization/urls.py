from django.urls import path
from .views import custom_cake_request, my_custom_cake_requests

urlpatterns = [
    path('', custom_cake_request, name='custom-cake-request'),
    path('my-requests/', my_custom_cake_requests, name='my-custom-cakes'),
]
