from django.urls import path
from .views import custom_cake_request, my_custom_cake_requests, all_custom_cake_requests, update_custom_cake_request

urlpatterns = [
    path('', custom_cake_request),
    path('my-requests/', my_custom_cake_requests),
    path('all/', all_custom_cake_requests),
    path('<int:pk>/update/', update_custom_cake_request),
]