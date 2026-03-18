from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .views import register, profile, change_password, update_fcm_token
from .views_jwt import CustomTokenObtainPairView

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='logout'),
    path('profile/', profile, name='profile'),
    path('change-password/', change_password, name='change-password'),
    path('fcm-token/', update_fcm_token, name='update-fcm-token'),
]
