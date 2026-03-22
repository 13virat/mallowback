from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category, ProductVariant
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

from rest_framework.permissions import IsAdminUser

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_category(request):
    data = request.data
    try:
        from django.utils.text import slugify
        category = Category.objects.create(
            name=data['name'],
            slug=data.get('slug') or slugify(data['name']),
            description=data.get('description', ''),
            image=request.FILES.get('image') or None,
        )
        return Response(CategorySerializer(category, context={'request': request}).data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_product(request):
    data = request.data
    try:
        import json
        product = Product.objects.create(
            name=data['name'],
            category_id=data['category'],
            description=data.get('description', ''),
            is_eggless=data.get('is_eggless', 'true') in [True, 'true', 'True'],
            is_available=data.get('is_available', 'true') in [True, 'true', 'True'],
            is_featured=data.get('is_featured', 'false') in [True, 'true', 'True'],
            image=request.FILES.get('image') or '',
        )
        variants_raw = data.get('variants', '[]')
        variants = json.loads(variants_raw) if isinstance(variants_raw, str) else variants_raw
        for v in variants:
            ProductVariant.objects.create(
                product=product,
                weight=v['weight'],
                price=v['price'],
                stock=v.get('stock', 0),
                low_stock_threshold=v.get('low_stock_threshold', 5),
                is_available=v.get('is_available', True),
                track_inventory=v.get('track_inventory', True),
            )
        return Response(ProductSerializer(product, context={'request': request}).data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def adjust_stock(request, pk):
    from .models import ProductVariant, StockAuditLog
    try:
        variant = ProductVariant.objects.get(id=pk)
    except ProductVariant.DoesNotExist:
        return Response({'error': 'Variant not found.'}, status=404)

    action = request.data.get('action', 'restock')  # restock | manual
    quantity = int(request.data.get('quantity', 0))
    notes = request.data.get('notes', '')

    if quantity <= 0:
        return Response({'error': 'Quantity must be greater than 0.'}, status=400)

    stock_before = variant.stock

    # Add stock
    from django.db.models import F
    ProductVariant.objects.filter(id=pk).update(stock=F('stock') + quantity)
    variant.refresh_from_db()

    stock_after = variant.stock

    # Write audit log
    StockAuditLog.objects.create(
        variant=variant,
        action='restock' if action == 'restock' else 'manual',
        quantity_change=+quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        performed_by=request.user,
        notes=notes,
    )

    return Response({
        'variant_id': pk,
        'product': variant.product.name,
        'weight': variant.weight,
        'stock_before': stock_before,
        'stock_after': stock_after,
        'quantity_added': quantity,
    })