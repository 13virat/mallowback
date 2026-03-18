from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    """
    List available products.
    Supports: ?category=<slug>  ?search=<term>  ?eggless=true  ?featured=true
    """
    products = Product.objects.filter(is_available=True).select_related('category').prefetch_related('variants')

    category_slug = request.query_params.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    search = request.query_params.get('search')
    if search:
        products = products.filter(name__icontains=search)

    if request.query_params.get('eggless') == 'true':
        products = products.filter(is_eggless=True)

    if request.query_params.get('featured') == 'true':
        products = products.filter(is_featured=True)

    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, pk):
    try:
        product = Product.objects.select_related('category').prefetch_related('variants').get(id=pk)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)
