from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Coupon, CouponUsage
from .serializers import ApplyCouponSerializer, CouponSerializer
from rest_framework.permissions import IsAdminUser

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_coupon(request):
    serializer = ApplyCouponSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    code = serializer.validated_data['code'].upper()
    order_amount = serializer.validated_data['order_amount']

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return Response({'error': 'Invalid coupon code.'}, status=status.HTTP_404_NOT_FOUND)

    if not coupon.is_valid():
        return Response({'error': 'Coupon is expired or no longer valid.'}, status=status.HTTP_400_BAD_REQUEST)

    if order_amount < coupon.min_order_amount:
        return Response({
            'error': f'Minimum order amount of ₹{coupon.min_order_amount} required.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check per-user usage
    user_uses = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
    if user_uses >= coupon.max_uses_per_user:
        return Response({'error': 'You have already used this coupon.'}, status=status.HTTP_400_BAD_REQUEST)

    discount = coupon.calculate_discount(order_amount)
    final_amount = order_amount - discount

    return Response({
        'coupon': CouponSerializer(coupon).data,
        'discount': discount,
        'final_amount': final_amount,
        'message': f'Coupon "{code}" applied! You save ₹{discount}.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_coupons(request):
    """List active coupons the user hasn't exhausted."""
    now = timezone.now()
    coupons = Coupon.objects.filter(is_active=True, valid_from__lte=now, valid_until__gte=now)
    serializer = CouponSerializer(coupons, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_coupon(request):
    data = request.data
    try:
        coupon = Coupon.objects.create(
            code=str(data['code']).upper(),
            coupon_type=data.get('coupon_type', 'percentage'),
            discount_value=data['discount_value'],
            min_order_amount=data.get('min_order_amount', 0),
            max_discount_amount=data.get('max_discount_amount') or None,
            max_uses=data.get('max_uses', 100),
            max_uses_per_user=data.get('max_uses_per_user', 1),
            valid_from=data['valid_from'],
            valid_until=data['valid_until'],
            description=data.get('description', ''),
            is_active=True,
        )
        return Response(CouponSerializer(coupon).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)