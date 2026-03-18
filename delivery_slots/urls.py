from django.urls import path
from .views import available_slots, book_slot, my_bookings, cancel_booking

urlpatterns = [
    path('', available_slots, name='slot-list'),
    path('book/', book_slot, name='slot-book'),
    path('my-bookings/', my_bookings, name='slot-my-bookings'),
    path('bookings/<int:pk>/', cancel_booking, name='slot-cancel'),
]
