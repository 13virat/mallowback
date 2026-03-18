"""
Delivery logic service — pincode validation, nearest store, distance calculation.
Uses Haversine formula for distance (no external API required).
"""
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points on Earth in kilometres.
    Uses Haversine formula — accurate enough for city-level delivery routing.
    """
    R = 6371.0  # Earth radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def check_pincode_serviceability(pincode: str) -> dict:
    """
    Check if a pincode is serviceable.
    Returns dict with: is_serviceable, delivery_charge, free_delivery_above,
                       estimated_time, nearest_store (or None).
    """
    from .models import ServiceablePincode

    sp = ServiceablePincode.objects.select_related('store').filter(
        pincode=pincode.strip(),
        store__is_active=True,
    ).first()

    if not sp:
        return {
            'is_serviceable': False,
            'pincode': pincode,
            'message': f"Sorry, we don't deliver to pincode {pincode} yet.",
        }

    return {
        'is_serviceable': True,
        'pincode': pincode,
        'delivery_charge': float(sp.delivery_charge),
        'free_delivery_above': float(sp.min_order_for_free_delivery),
        'estimated_time': sp.estimated_delivery_time,
        'nearest_store': {
            'id': sp.store.id,
            'name': sp.store.name,
            'address': sp.store.address,
            'phone': sp.store.phone,
        },
    }


def find_nearest_store(lat: float, lon: float) -> Optional[object]:
    """
    Find the nearest active store to a given coordinate.
    Returns StoreLocation instance or None.
    """
    from .models import StoreLocation

    stores = StoreLocation.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    nearest = None
    min_dist = float('inf')

    for store in stores:
        dist = haversine_km(lat, lon, float(store.latitude), float(store.longitude))
        if dist < min_dist:
            min_dist = dist
            nearest = store

    return nearest


def get_stores_with_distance(lat: float, lon: float) -> list:
    """
    Return all active stores sorted by distance from a coordinate.
    Each entry includes distance_km.
    """
    from .models import StoreLocation

    stores = StoreLocation.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    result = []
    for store in stores:
        dist = haversine_km(lat, lon, float(store.latitude), float(store.longitude))
        result.append({'store': store, 'distance_km': round(dist, 2)})

    result.sort(key=lambda x: x['distance_km'])
    return result
