from django.urls import path
from .views import store_list, check_pincode, store_pincodes

urlpatterns = [
    path('', store_list, name='store-list'),
    path('check-pincode/', check_pincode, name='store-check-pincode'),
    path('<int:pk>/pincodes/', store_pincodes, name='store-pincodes'),
]
