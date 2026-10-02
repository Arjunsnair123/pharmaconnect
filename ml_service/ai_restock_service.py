import logging
from collections import defaultdict

from django.conf import settings
from django.core.cache import cache

from ml.demand_forecast import ModelNotTrained, predict_next_week_demand
from ml_service.spatial_allocator import allocate_weekly_stock
from inventory.models import Inventory

logger = logging.getLogger(__name__)

RESTOCK_CACHE_KEY = "ai_restock:v1"


def invalidate_restock_cache():
    cache.delete(RESTOCK_CACHE_KEY)


def generate_ai_restock():
    """
    Restock suggestions for every pharmacy, cached.

    The result depends on the trained model, the search logs and current
    stock. Stock changes and retraining invalidate the cache explicitly;
    new searches are picked up when the timeout expires.
    """
    result = cache.get(RESTOCK_CACHE_KEY)
    if result is None:
        try:
            result = _compute_ai_restock()
        except ModelNotTrained as exc:
            # Suggestions are an extra; the dashboard must still load.
            # Not cached, so they appear as soon as the model is trained.
            logger.warning("Restock suggestions unavailable: %s", exc)
            return {"total_area_demand": None, "pharmacy_allocation": {}}
        cache.set(RESTOCK_CACHE_KEY, result, settings.RESTOCK_CACHE_TIMEOUT)
    return result


def _compute_ai_restock():

    # Step 1: Predict next week demand
    total_weekly_demand, predictions = predict_next_week_demand()

    # Step 2: Allocate demand to pharmacies (keyed by pharmacy id)
    allocation = allocate_weekly_stock(total_weekly_demand)

    # Current stock for every allocated pharmacy in one query
    current_stock = defaultdict(dict)
    stock_rows = Inventory.objects.filter(pharmacy_id__in=allocation.keys()) \
        .values_list("pharmacy_id", "medicine__brand_name", "quantity")
    for pharmacy_id, brand_name, quantity in stock_rows:
        current_stock[pharmacy_id][brand_name] = quantity

    filtered_allocation = {}

    for pharmacy_id, medicines in allocation.items():

        pharmacy_suggestions = {}

        for med_name, predicted_qty in medicines.items():

            restock_needed = predicted_qty - current_stock[pharmacy_id].get(med_name, 0)

            # Only suggest if stock is less than predicted demand
            if restock_needed > 0:
                pharmacy_suggestions[med_name] = restock_needed

        if pharmacy_suggestions:
            filtered_allocation[pharmacy_id] = pharmacy_suggestions

    return {
        "total_area_demand": total_weekly_demand,
        "pharmacy_allocation": filtered_allocation
    }
