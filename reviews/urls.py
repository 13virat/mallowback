from django.urls import path
from .views import add_review, product_reviews, delete_review

urlpatterns = [
    path('', add_review, name='review-add'),
    path('product/<int:product_id>/', product_reviews, name='product-reviews'),
    path('<int:pk>/delete/', delete_review, name='review-delete'),
]
