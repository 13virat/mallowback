"""
Product/Inventory business logic service layer.
All stock operations go through here — never manipulate stock directly in views.
"""
import logging
from django.db import transaction
from .models import ProductVariant, StockAuditLog

logger = logging.getLogger('products')


def deduct_stock_for_order(order):
    """
    Atomically deduct stock for every item in a confirmed order.
    If any variant is out of stock, the entire operation is rolled back.
    Logs every change in StockAuditLog.
    """
    with transaction.atomic():
        for item in order.items.select_related('variant__product').all():
            variant = item.variant
            stock_before = variant.stock

            try:
                variant.deduct_stock(item.quantity)
            except ValueError as e:
                logger.error(f"Stock deduction failed for order #{order.id}: {e}")
                raise  # Roll back entire transaction

            StockAuditLog.objects.create(
                variant=variant,
                action='sale',
                quantity_change=-item.quantity,
                stock_before=stock_before,
                stock_after=variant.stock,
                order=order,
            )
            logger.info(
                f"Stock deducted: {variant} | qty={item.quantity} | "
                f"before={stock_before} after={variant.stock}"
            )


def restore_stock_for_order(order, performed_by=None):
    """
    Restore stock when an order is cancelled.
    """
    with transaction.atomic():
        for item in order.items.select_related('variant').all():
            variant = item.variant
            stock_before = variant.stock
            variant.restore_stock(item.quantity)

            StockAuditLog.objects.create(
                variant=variant,
                action='cancel',
                quantity_change=+item.quantity,
                stock_before=stock_before,
                stock_after=variant.stock,
                order=order,
                performed_by=performed_by,
            )
            logger.info(f"Stock restored: {variant} | qty={item.quantity}")


def adjust_stock_manually(variant_id: int, quantity_delta: int, performed_by, notes: str = ''):
    """
    Manual stock adjustment by admin. quantity_delta can be positive or negative.
    """
    with transaction.atomic():
        variant = ProductVariant.objects.select_for_update().get(id=variant_id)
        new_stock = variant.stock + quantity_delta

        if new_stock < 0:
            raise ValueError(f"Adjustment would result in negative stock ({new_stock}).")

        stock_before = variant.stock
        variant.stock = new_stock
        variant.save()

        StockAuditLog.objects.create(
            variant=variant,
            action='manual',
            quantity_change=quantity_delta,
            stock_before=stock_before,
            stock_after=new_stock,
            performed_by=performed_by,
            notes=notes,
        )
        return variant


def check_cart_stock(cart):
    """
    Validate that all cart items have sufficient stock before order placement.
    Returns list of error strings. Empty list means all items are available.
    """
    errors = []
    for item in cart.items.select_related('variant__product').all():
        variant = item.variant
        if not variant.is_available:
            errors.append(f"'{variant.product.name} ({variant.weight})' is currently unavailable.")
            continue
        if variant.track_inventory and variant.available_stock < item.quantity:
            errors.append(
                f"'{variant.product.name} ({variant.weight})' — only "
                f"{variant.available_stock} unit(s) available, you requested {item.quantity}."
            )
    return errors
