from django.urls import path
from .views import available_slots, book_slot, my_bookings, cancel_booking, all_slots, create_slot, update_slot, all_bookings

urlpatterns = [
    path('', available_slots),
    path('all/', all_slots),
    path('create/', create_slot),
    path('<int:pk>/update/', update_slot),
    path('book/', book_slot),
    path('my-bookings/', my_bookings),
    path('all-bookings/', all_bookings),
    path('bookings/<int:pk>/', cancel_booking),
]
