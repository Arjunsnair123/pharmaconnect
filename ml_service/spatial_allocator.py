from collections import defaultdict
from ml_service.models import SearchLog

def allocate_weekly_stock(total_weekly_demand):
    """
    Distributes total area demand to each pharmacy and medicine
    using spatial search frequency stored in SearchLog.

    Returns {pharmacy_id: {medicine_name: units}}. Keyed by id because
    pharmacy names are not unique (two branches can share a name).
    """

    logs = list(SearchLog.objects.values_list("medicine", "nearest_pharmacy_id"))

    medicine_counts = defaultdict(int)
    for medicine, _ in logs:
        medicine_counts[medicine] += 1

    total_searches = sum(medicine_counts.values())
    if total_searches == 0:
        return {}

    pharmacy_medicine_counts = defaultdict(lambda: defaultdict(int))

    for medicine, pharmacy_id in logs:
        # Searches with no nearby pharmacy still count towards a medicine's
        # overall demand above, but there is nobody to allocate them to.
        if pharmacy_id is None:
            continue
        pharmacy_medicine_counts[pharmacy_id][medicine] += 1

    allocation = {}

    for pharmacy_id, meds in pharmacy_medicine_counts.items():
        allocation[pharmacy_id] = {}

        for med, count in meds.items():
            med_share = medicine_counts[med] / total_searches
            pharmacy_share = count / medicine_counts[med]
            final_units = round(total_weekly_demand * med_share * pharmacy_share)
            allocation[pharmacy_id][med] = final_units

    return allocation
