import math

KM_PER_DEGREE_LAT = 111.32


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in KM
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def bounding_box_filter(lat, lon, radius_km, prefix=""):
    """
    Queryset filter kwargs for the lat/lon square that encloses a circle of
    radius_km around (lat, lon). It is a cheap, index-friendly prefilter that
    lets the database discard far-away rows; callers still run haversine on
    what is left to get exact distances and trim the square's corners.

    prefix is the lookup path to the Pharmacy fields, e.g. "pharmacy__".
    """
    dlat = radius_km / KM_PER_DEGREE_LAT
    filters = {
        f"{prefix}latitude__gte": lat - dlat,
        f"{prefix}latitude__lte": lat + dlat,
    }

    # A degree of longitude shrinks with cos(latitude). Near the poles, or if
    # the box would cross the antimeridian, skip the longitude bound rather
    # than wrongly exclude rows; haversine still gives the right answer.
    cos_lat = math.cos(math.radians(lat))
    if cos_lat > 0.01:
        dlon = radius_km / (KM_PER_DEGREE_LAT * cos_lat)
        if lon - dlon >= -180 and lon + dlon <= 180:
            filters[f"{prefix}longitude__gte"] = lon - dlon
            filters[f"{prefix}longitude__lte"] = lon + dlon

    return filters

