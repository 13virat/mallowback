from django.urls import path
from .views import my_loyalty, redeem_points

urlpatterns = [
    path('', my_loyalty, name='loyalty'),
    path('redeem/', redeem_points, name='loyalty-redeem'),
]
