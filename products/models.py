"""
Product models — with full inventory management.
"""
from django.conf import settings
from django.db import models
from django.db.models import F


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    is_eggless = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    weight = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)

    # ── INVENTORY ──────────────────────────────────────────────────────────
    stock = models.PositiveIntegerField(default=0, help_text="Units in stock. 0 = out of stock.")
    reserved_stock = models.PositiveIntegerField(
        default=0,
        help_text="Units reserved for pending orders (not yet confirmed)."
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Send low-stock alert when stock falls to this level."
    )
    track_inventory = models.BooleanField(
        default=True,
        help_text="If False, inventory is not tracked (always in stock)."
    )

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.product.name} - {self.weight}"

    @property
    def available_stock(self):
        """Actual purchasable stock (total minus reserved)."""
        return max(0, self.stock - self.reserved_stock)

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.available_stock > 0

    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return 0 < self.stock <= self.low_stock_threshold

    def deduct_stock(self, quantity: int):
        """
        Atomically deduct stock. Raises ValueError if insufficient stock.
        Uses F() expression to avoid race conditions.
        """
        if not self.track_inventory:
            return

        # Atomic check-and-deduct
        updated = ProductVariant.objects.filter(
            id=self.id,
            stock__gte=quantity
        ).update(stock=F('stock') - quantity)

        if not updated:
            self.refresh_from_db()
            raise ValueError(
                f"Insufficient stock for {self.product.name} ({self.weight}). "
                f"Available: {self.stock}"
            )

        self.refresh_from_db()

        # Send low-stock alert if threshold crossed
        if self.is_low_stock:
            try:
                from products.tasks import send_low_stock_alert_task
                send_low_stock_alert_task.delay(self.id)
            except Exception:
                pass

    def restore_stock(self, quantity: int):
        """Return stock (e.g., on order cancellation)."""
        if not self.track_inventory:
            return
        ProductVariant.objects.filter(id=self.id).update(stock=F('stock') + quantity)
        self.refresh_from_db()


class StockAuditLog(models.Model):
    """Full audit trail for every stock change."""
    ACTION_CHOICES = (
        ('sale', 'Sale (Order Placed)'),
        ('cancel', 'Cancellation (Stock Restored)'),
        ('manual', 'Manual Adjustment'),
        ('restock', 'Restock'),
    )

    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity_change = models.IntegerField(help_text="Negative for deductions, positive for additions.")
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.variant} | {self.action} | {self.quantity_change:+d}"
