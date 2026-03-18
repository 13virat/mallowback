from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Admin site customisation
admin.site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'Cakemallow Operations')
admin.site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Cakemallow Admin')
admin.site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Dashboard')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check
    path('api/', include('core.urls')),

    # Auth
    path('api/auth/', include('accounts.urls')),

    # Catalog
    path('api/products/', include('products.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/custom-cake/', include('customization.urls')),
    path('api/reviews/', include('reviews.urls')),

    # Commerce
    path('api/payments/', include('payments.urls')),
    path('api/coupons/', include('coupons.urls')),
    path('api/loyalty/', include('loyalty.urls')),
    path('api/wishlist/', include('wishlist.urls')),

    # Logistics
    path('api/delivery-slots/', include('delivery_slots.urls')),
    path('api/stores/', include('store_locations.urls')),

    # Comms & Intelligence
    path('api/notifications/', include('notifications.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/otp/', include('otp.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
