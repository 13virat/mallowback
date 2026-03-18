from django.urls import path
from .views import product_list, category_list, product_detail

urlpatterns = [
    path('', product_list, name='product-list'),
    path('categories/', category_list, name='category-list'),
    path('<int:pk>/', product_detail, name='product-detail'),
]
