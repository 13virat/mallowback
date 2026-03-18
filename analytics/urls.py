from django.urls import path
from .views import (
    dashboard_summary, revenue_chart, top_products,
    order_status_breakdown, inventory_report, recent_orders, payment_report,
)

urlpatterns = [
    path('summary/', dashboard_summary, name='analytics-summary'),
    path('revenue/', revenue_chart, name='analytics-revenue'),
    path('top-products/', top_products, name='analytics-top-products'),
    path('order-status/', order_status_breakdown, name='analytics-order-status'),
    path('inventory/', inventory_report, name='analytics-inventory'),
    path('recent-orders/', recent_orders, name='analytics-recent-orders'),
    path('payments/', payment_report, name='analytics-payments'),
]
