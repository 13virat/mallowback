from django.urls import path
from .views import my_wishlist, toggle_wishlist

urlpatterns = [
    path('', my_wishlist, name='wishlist'),
    path('toggle/<int:product_id>/', toggle_wishlist, name='wishlist-toggle'),
]
