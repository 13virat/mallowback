from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import StoreLocation, ServiceablePincode
from .serializers import StoreLocationSerializer, ServiceablePincodeSerializer
from .services import check_pincode_serviceability, get_stores_with_distance
from rest_framework.permissions import IsAdminUser

@api_view(['GET'])
@permission_classes([AllowAny])
def store_list(request):
    """GET /api/stores/ — optionally ?lat=<>&lon=<> for distance-sorted results."""
    stores = StoreLocation.objects.filter(is_active=True).prefetch_related('pincodes')

    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')

    if lat and lon:
        try:
            results = get_stores_with_distance(float(lat), float(lon))
            data = []
            for item in results:
                s = StoreLocationSerializer(item['store']).data
                s['distance_km'] = item['distance_km']
                data.append(s)
            return Response(data)
        except (ValueError, TypeError):
            pass

    return Response(StoreLocationSerializer(stores, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_pincode(request):
    """
    GET /api/stores/check-pincode/?pincode=226001
    Returns serviceability, delivery charge, estimated time.
    """
    pincode = request.query_params.get('pincode', '').strip()
    if not pincode:
        return Response({'error': 'pincode query param required.'}, status=status.HTTP_400_BAD_REQUEST)

    result = check_pincode_serviceability(pincode)
    status_code = status.HTTP_200_OK if result['is_serviceable'] else status.HTTP_404_NOT_FOUND
    return Response(result, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def store_pincodes(request, pk):
    """GET /api/stores/<pk>/pincodes/ — list all pincodes served by a store."""
    try:
        store = StoreLocation.objects.get(id=pk, is_active=True)
    except StoreLocation.DoesNotExist:
        return Response({'error': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

    pincodes = store.pincodes.all()
    return Response(ServiceablePincodeSerializer(pincodes, many=True).data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_store(request):
    data = request.data
    try:
        store = StoreLocation.objects.create(
            name=data['name'],
            address=data['address'],
            city=data['city'],
            pincode=data.get('pincode', ''),
            phone=data['phone'],
            email=data.get('email', ''),
            latitude=data.get('latitude') or None,
            longitude=data.get('longitude') or None,
            opening_time=data.get('opening_time', '09:00'),
            closing_time=data.get('closing_time', '21:00'),
            is_open_sunday=data.get('is_open_sunday', False),
            is_active=data.get('is_active', True),
        )
        # Create serviceable pincodes if provided
        for p in data.get('pincodes', []):
            if p.get('pincode'):
                ServiceablePincode.objects.create(
                    store=store,
                    pincode=p['pincode'],
                    delivery_charge=p.get('delivery_charge', 0),
                    min_order_for_free_delivery=p.get('min_order_for_free_delivery', 0),
                    estimated_delivery_time=p.get('estimated_delivery_time', '2-4 hours'),
                )
        return Response(StoreLocationSerializer(store).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)