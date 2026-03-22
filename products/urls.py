from django.urls import path
from .views import (
    product_list, category_list, product_detail,
    create_product, create_category, adjust_stock, update_category, update_product, update_variant,
)

urlpatterns = [
    path('', product_list, name='product-list'),
    path('categories/', category_list, name='category-list'),
    path('categories/create/', create_category, name='category-create'),
    path('create/', create_product, name='product-create'),
    path('<int:pk>/', product_detail, name='product-detail'),
    path('variants/<int:pk>/adjust-stock/', adjust_stock, name='variant-adjust-stock'),
    path('<int:pk>/update/', update_product, name='product-update'),
    path('categories/<int:pk>/update/', update_category, name='category-update'),
    path('variants/<int:pk>/update/', update_variant, name='variant-update'),
]