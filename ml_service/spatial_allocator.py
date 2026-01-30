from collections import defaultdict
from ml_service.models import SearchLog

def allocate_weekly_stock(total_weekly_demand):
    """
    Distributes total area demand to each pharmacy and medicine
    using spatial search frequency stored in SearchLog.
    """

    logs = SearchLog.objects.all()

    medicine_counts = defaultdict(int)
    for log in logs:
        medicine_counts[log.medicine] += 1

    total_searches = sum(medicine_counts.values())
    if total_searches == 0:
        return {}

    pharmacy_medicine_counts = defaultdict(lambda: defaultdict(int))

    for log in logs:
        pharmacy_name = log.nearest_pharmacy.name
        pharmacy_medicine_counts[pharmacy_name][log.medicine] += 1

    allocation = {}

    for pharmacy_name, meds in pharmacy_medicine_counts.items():
        allocation[pharmacy_name] = {}

        for med, count in meds.items():
            med_share = medicine_counts[med] / total_searches
            pharmacy_share = count / medicine_counts[med]
            final_units = round(total_weekly_demand * med_share * pharmacy_share)
            allocation[pharmacy_name][med] = final_units

    return allocation
