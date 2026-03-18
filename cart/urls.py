from django.urls import path
from .views import view_cart, add_to_cart, cart_item_detail, clear_cart

urlpatterns = [
    path('', view_cart, name='cart'),
    path('add/', add_to_cart, name='cart-add'),
    path('items/<int:item_id>/', cart_item_detail, name='cart-item-detail'),
    path('clear/', clear_cart, name='cart-clear'),
]
