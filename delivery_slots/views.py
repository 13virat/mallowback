"""
Delivery slot views — atomic booking with select_for_update to prevent overbooking.
"""
from datetime import date as date_cls
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import DeliverySlot, SlotBooking
from .serializers import DeliverySlotSerializer, SlotBookingSerializer

from rest_framework.permissions import IsAdminUser


@api_view(['GET'])
@permission_classes([AllowAny])
def available_slots(request):
    """
    GET /api/delivery-slots/?date=2024-12-25
    Returns slots available on the given date with remaining capacity.
    """
    date_str = request.query_params.get('date')
    if not date_str:
        return Response(
            {'error': 'date query param required (YYYY-MM-DD).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        target_date = date_cls.fromisoformat(date_str)
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if target_date < date_cls.today():
        return Response(
            {'error': 'Cannot book slots for past dates.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    slots = DeliverySlot.objects.filter(is_active=True)
    available = [s for s in slots if s.is_available_on(target_date)]
    serializer = DeliverySlotSerializer(available, many=True, context={'date': date_str})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_slot(request):
    """
    POST /api/delivery-slots/book/
    { order_id, slot_id, delivery_date }

    Race-condition safe:
    - select_for_update() locks the DeliverySlot row
    - Re-checks capacity inside the atomic block
    - update_or_create prevents duplicate bookings per order
    """
    order_id = request.data.get('order_id')
    slot_id = request.data.get('slot_id')
    date_str = request.data.get('delivery_date')

    if not all([order_id, slot_id, date_str]):
        return Response(
            {'error': 'order_id, slot_id and delivery_date are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        target_date = date_cls.fromisoformat(date_str)
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if target_date < date_cls.today():
        return Response(
            {'error': 'Cannot book slots for past dates.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # Lock the slot row — prevents concurrent overbooking
            try:
                slot = DeliverySlot.objects.select_for_update().get(id=slot_id)
            except DeliverySlot.DoesNotExist:
                return Response({'error': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Re-verify availability inside the lock (double-check after acquiring lock)
            if not slot.is_available_on(target_date):
                return Response(
                    {'error': 'Selected slot is fully booked or unavailable on this date.'},
                    status=status.HTTP_409_CONFLICT
                )

            booking, created = SlotBooking.objects.update_or_create(
                order=order,
                defaults={
                    'slot': slot,
                    'delivery_date': target_date,
                }
            )

    except Exception as e:
        return Response(
            {'error': 'Booking failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        SlotBookingSerializer(booking).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    """GET /api/delivery-slots/my-bookings/ — list all slot bookings for current user."""
    bookings = SlotBooking.objects.filter(
        order__user=request.user
    ).select_related('slot', 'order').order_by('-delivery_date')
    return Response(SlotBookingSerializer(bookings, many=True).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, pk):
    """DELETE /api/delivery-slots/bookings/<pk>/ — cancel a slot booking."""
    try:
        booking = SlotBooking.objects.get(id=pk, order__user=request.user)
    except SlotBooking.DoesNotExist:
        return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

    if booking.delivery_date < date_cls.today():
        return Response(
            {'error': 'Cannot cancel past bookings.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    booking.delete()
    return Response({'message': 'Slot booking cancelled.'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_slots(request):
    """Admin: list all slots (active + inactive)"""
    slots = DeliverySlot.objects.all()
    return Response(DeliverySlotSerializer(slots, many=True).data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_slot(request):
    data = request.data
    try:
        slot = DeliverySlot.objects.create(
            label=data['label'], start_time=data['start_time'],
            end_time=data['end_time'], max_orders=data.get('max_orders', 10),
            extra_charge=data.get('extra_charge', 0),
            available_days=data.get('available_days', list(range(7))),
            is_active=data.get('is_active', True),
        )
        return Response(DeliverySlotSerializer(slot).data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_slot(request, pk):
    try:
        slot = DeliverySlot.objects.get(id=pk)
        for f in ['label','start_time','end_time','max_orders','extra_charge','available_days','is_active']:
            if f in request.data:
                setattr(slot, f, request.data[f])
        slot.save()
        return Response(DeliverySlotSerializer(slot).data)
    except DeliverySlot.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_bookings(request):
    """Admin: list all slot bookings across all users"""
    bookings = SlotBooking.objects.select_related('slot','order').order_by('-delivery_date')
    return Response(SlotBookingSerializer(bookings, many=True).data)