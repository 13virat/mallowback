from django.urls import path
from .views import store_list, check_pincode, store_pincodes, create_store

urlpatterns = [
    path('', store_list, name='store-list'),
    path('check-pincode/', check_pincode, name='store-check-pincode'),
    path('create/', create_store, name='store-create'),
    path('<int:pk>/pincodes/', store_pincodes, name='store-pincodes'),
]
