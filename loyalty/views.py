from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import LoyaltyAccount
from .serializers import LoyaltyAccountSerializer
from rest_framework.permissions import IsAdminUser

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_loyalty(request):
    account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    return Response(LoyaltyAccountSerializer(account).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_points(request):
    points_to_redeem = int(request.data.get('points', 0))
    if points_to_redeem <= 0:
        return Response({'error': 'Enter a valid number of points.'}, status=status.HTTP_400_BAD_REQUEST)

    account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    try:
        discount = account.redeem_points(points_to_redeem, description='Redeemed at checkout')
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'points_redeemed': points_to_redeem,
        'discount_applied': discount,
        'remaining_points': account.points,
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_loyalty_accounts(request):
    from .models import LoyaltyAccount
    accounts = LoyaltyAccount.objects.select_related('user').prefetch_related('transactions').all()
    data = []
    for acc in accounts:
        d = LoyaltyAccountSerializer(acc).data
        d['user_email'] = acc.user.email
        d['user_name'] = f"{acc.user.first_name} {acc.user.last_name}".strip()
        d['id'] = acc.id
        data.append(d)
    return Response(data)