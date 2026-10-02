from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from inventory.models import Inventory
from ml_service.ai_restock_service import invalidate_restock_cache


@receiver([post_save, post_delete], sender=Inventory)
def clear_restock_cache_on_stock_change(sender, **kwargs):
    # Suggestions are "predicted demand minus current stock", so any stock
    # edit (web UI or Django admin) makes the cached copy stale.
    invalidate_restock_cache()
