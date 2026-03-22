from django.urls import path
from .views import (
    custom_cake_request,
    my_custom_cake_requests,
    all_custom_cake_requests,
    update_custom_cake_request,
)

urlpatterns = [
    path('', custom_cake_request, name='custom-cake-request'),
    path('my-requests/', my_custom_cake_requests, name='my-custom-cakes'),
    path('all/', all_custom_cake_requests, name='all-custom-cakes'),
    path('<int:pk>/update/', update_custom_cake_request, name='update-custom-cake'),
]