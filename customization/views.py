from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .models import CustomCakeRequest
from .serializers import CustomCakeSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_cake_request(request):
    serializer = CustomCakeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user if request.user.is_authenticated else None
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_custom_cake_requests(request):
    reqs = CustomCakeRequest.objects.filter(user=request.user)
    serializer = CustomCakeSerializer(reqs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_custom_cake_requests(request):
    """Admin: list all custom cake requests across all users."""
    reqs = CustomCakeRequest.objects.select_related('user').all()
    serializer = CustomCakeSerializer(reqs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_custom_cake_request(request, pk):
    """Admin: update status and admin_notes."""
    try:
        req = CustomCakeRequest.objects.get(id=pk)
        if 'status' in request.data:
            req.status = request.data['status']
        if 'admin_notes' in request.data:
            req.admin_notes = request.data['admin_notes']
        req.save()
        return Response(CustomCakeSerializer(req, context={'request': request}).data)
    except CustomCakeRequest.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)