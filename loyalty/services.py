"""
Loyalty points service — award, redeem, tier management.
"""
import logging
from .models import LoyaltyAccount, PointTransaction

logger = logging.getLogger(__name__)

POINTS_PER_RUPEE = 0.1       # 1 point per ₹10
RUPEES_PER_POINT = 0.5       # 2 points = ₹1 discount


def award_points_for_payment(user, amount, order_id: int):
    """Award loyalty points after a successful payment."""
    points_earned = max(1, int(float(amount) * POINTS_PER_RUPEE))
    account, _ = LoyaltyAccount.objects.get_or_create(user=user)
    account.add_points(points_earned, description=f'Order #{order_id} payment')
    logger.info(f"Awarded {points_earned} points to user #{user.id} for order #{order_id}")
    return points_earned


def redeem_points(user, points_to_redeem: int, order_id: int) -> float:
    """
    Redeem loyalty points. Returns the rupee discount value.
    Raises ValueError if insufficient points.
    """
    account = LoyaltyAccount.objects.get(user=user)
    rupee_discount = account.redeem_points(
        points_to_redeem,
        description=f'Redeemed for order #{order_id}'
    )
    logger.info(f"Redeemed {points_to_redeem} points for user #{user.id} — ₹{rupee_discount} discount")
    return rupee_discount
