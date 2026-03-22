from django.urls import path
from .views import all_loyalty_accounts, my_loyalty, redeem_points

urlpatterns = [
    path('', my_loyalty, name='loyalty'),
    path('redeem/', redeem_points, name='loyalty-redeem'),
    path('all/', all_loyalty_accounts, name='loyalty-all'),
]
