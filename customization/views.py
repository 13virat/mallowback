from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import CustomCakeRequest
from .serializers import CustomCakeSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_cake_request(request):
    serializer = CustomCakeSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user if request.user.is_authenticated else None
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_custom_cake_requests(request):
    requests = CustomCakeRequest.objects.filter(user=request.user)
    serializer = CustomCakeSerializer(requests, many=True, context={'request': request})
    return Response(serializer.data)
