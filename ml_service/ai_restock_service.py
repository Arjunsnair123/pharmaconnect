from ml.demand_forecast import predict_next_week_demand
from ml_service.spatial_allocator import allocate_weekly_stock
from inventory.models import Inventory
from pharmacies.models import Pharmacy


def generate_ai_restock():

    # Step 1: Predict next week demand
    total_weekly_demand, predictions = predict_next_week_demand()

    # Step 2: Allocate demand to pharmacies
    allocation = allocate_weekly_stock(total_weekly_demand)

    filtered_allocation = {}

    for pharmacy_name, medicines in allocation.items():

        try:
            pharmacy = Pharmacy.objects.get(name=pharmacy_name)
        except Pharmacy.DoesNotExist:
            continue

        pharmacy_suggestions = {}

        for med_name, predicted_qty in medicines.items():

            inventory = Inventory.objects.filter(
                pharmacy=pharmacy,
                medicine__brand_name=med_name
            ).first()

            current_stock = inventory.quantity if inventory else 0

            restock_needed = predicted_qty - current_stock

            # Only suggest if stock is less than predicted demand
            if restock_needed > 0:
                pharmacy_suggestions[med_name] = restock_needed

        if pharmacy_suggestions:
            filtered_allocation[pharmacy_name] = pharmacy_suggestions

    return {
        "total_area_demand": total_weekly_demand,
        "pharmacy_allocation": filtered_allocation
    }