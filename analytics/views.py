"""
Analytics API — admin-only KPIs, charts, reports.
All queries use select_related/prefetch to avoid N+1.
"""
from datetime import date, timedelta
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from orders.models import Order, OrderItem
from accounts.models import User
from products.models import Product, ProductVariant
from payments.models import Payment


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_summary(request):
    """GET /api/analytics/summary/ — High-level KPIs."""
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    orders_today = Order.objects.filter(created_at__date=today)
    orders_month = Order.objects.filter(created_at__date__gte=month_start)
    orders_week = Order.objects.filter(created_at__date__gte=week_start)

    def revenue(qs):
        return float(qs.filter(status='delivered').aggregate(t=Sum('final_amount'))['t'] or 0)

    pending_orders = Order.objects.filter(status__in=['pending', 'confirmed', 'preparing']).count()
    low_stock_variants = ProductVariant.objects.filter(
        track_inventory=True,
        stock__lte=F('low_stock_threshold'),
        stock__gt=0,
    ).count()
    out_of_stock = ProductVariant.objects.filter(track_inventory=True, stock=0).count()

    return Response({
        'orders_today': orders_today.count(),
        'orders_this_week': orders_week.count(),
        'orders_this_month': orders_month.count(),
        'revenue_today': round(revenue(orders_today), 2),
        'revenue_this_week': round(revenue(orders_week), 2),
        'revenue_this_month': round(revenue(orders_month), 2),
        'pending_orders': pending_orders,
        'avg_order_value': round(float(
            Order.objects.filter(status='delivered').aggregate(avg=Avg('final_amount'))['avg'] or 0
        ), 2),
        'new_users_this_month': User.objects.filter(date_joined__date__gte=month_start).count(),
        'total_customers': User.objects.filter(is_staff=False).count(),
        'total_products': Product.objects.filter(is_available=True).count(),
        'low_stock_alerts': low_stock_variants,
        'out_of_stock_variants': out_of_stock,
        'total_payments_today': Payment.objects.filter(
            status='success', created_at__date=today
        ).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def revenue_chart(request):
    """GET /api/analytics/revenue/?period=daily|weekly|monthly"""
    period = request.query_params.get('period', 'daily')

    if period == 'monthly':
        since = date.today().replace(day=1) - timedelta(days=365)
        data = (
            Order.objects
            .filter(status='delivered', created_at__date__gte=since)
            .annotate(period=TruncMonth('created_at'))
            .values('period')
            .annotate(revenue=Sum('final_amount'), orders=Count('id'))
            .order_by('period')
        )
    elif period == 'weekly':
        since = date.today() - timedelta(weeks=12)
        data = (
            Order.objects
            .filter(status='delivered', created_at__date__gte=since)
            .annotate(period=TruncWeek('created_at'))
            .values('period')
            .annotate(revenue=Sum('final_amount'), orders=Count('id'))
            .order_by('period')
        )
    else:  # daily
        since = date.today() - timedelta(days=29)
        data = (
            Order.objects
            .filter(status='delivered', created_at__date__gte=since)
            .annotate(period=TruncDate('created_at'))
            .values('period')
            .annotate(revenue=Sum('final_amount'), orders=Count('id'))
            .order_by('period')
        )

    return Response(list(data))


@api_view(['GET'])
@permission_classes([IsAdminUser])
def top_products(request):
    """GET /api/analytics/top-products/?limit=10"""
    limit = min(int(request.query_params.get('limit', 10)), 50)
    data = (
        OrderItem.objects
        .filter(order__status='delivered')
        .values('product__id', 'product__name', 'product__category__name')
        .annotate(
            units_sold=Sum('quantity'),
            total_revenue=Sum(F('price') * F('quantity')),
        )
        .order_by('-units_sold')[:limit]
    )
    return Response(list(data))


@api_view(['GET'])
@permission_classes([IsAdminUser])
def order_status_breakdown(request):
    """GET /api/analytics/order-status/"""
    data = Order.objects.values('status').annotate(count=Count('id')).order_by('status')
    return Response(list(data))


@api_view(['GET'])
@permission_classes([IsAdminUser])
def inventory_report(request):
    """GET /api/analytics/inventory/ — Stock levels across all variants."""
    variants = ProductVariant.objects.select_related('product__category').filter(
        track_inventory=True
    ).order_by('stock')

    result = []
    for v in variants:
        result.append({
            'id': v.id,
            'product': v.product.name,
            'category': v.product.category.name,
            'weight': v.weight,
            'stock': v.stock,
            'available_stock': v.available_stock,
            'status': 'out_of_stock' if v.stock == 0 else ('low' if v.is_low_stock else 'ok'),
            'low_stock_threshold': v.low_stock_threshold,
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_orders(request):
    """GET /api/analytics/recent-orders/?limit=20"""
    limit = min(int(request.query_params.get('limit', 20)), 100)
    from orders.serializers import OrderSerializer
    orders = Order.objects.select_related('user', 'address').prefetch_related('items').order_by('-created_at')[:limit]
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def payment_report(request):
    """GET /api/analytics/payments/ — payment method and status breakdown."""
    by_method = Payment.objects.values('method').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    by_status = Payment.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    return Response({'by_method': list(by_method), 'by_status': list(by_status)})
