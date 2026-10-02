"""Shared API building blocks: query-param validation and pagination."""
import math

from django.conf import settings
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def paginate(view, request, items):
    """
    Paginate a queryset or list inside a plain APIView.
    Returns (page_items, envelope) where envelope holds count/next/previous.
    """
    paginator = StandardPagination()
    page = paginator.paginate_queryset(items, request, view=view)
    envelope = {
        "count": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
    }
    return page, envelope


class LocationQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    radius_km = serializers.FloatField(
        required=False, help_text="Search radius in km. Defaults to the server setting."
    )

    def validate(self, attrs):
        # float() accepts "nan" and "inf", and NaN slips past min/max checks.
        for field in ("lat", "lon", "radius_km"):
            if field in attrs and not math.isfinite(attrs[field]):
                raise serializers.ValidationError({field: "Must be a finite number."})

        radius = attrs.setdefault("radius_km", settings.DEFAULT_SEARCH_RADIUS_KM)
        if not 0 < radius <= settings.MAX_SEARCH_RADIUS_KM:
            raise serializers.ValidationError({
                "radius_km": f"Must be greater than 0 and at most {settings.MAX_SEARCH_RADIUS_KM:g}."
            })
        return attrs


class AvailabilityQuerySerializer(LocationQuerySerializer):
    medicine = serializers.CharField(help_text="Exact brand name (case-insensitive).")
    emergency = serializers.BooleanField(
        default=False, help_text="Only include 24x7 pharmacies."
    )


class BrandQuerySerializer(serializers.Serializer):
    brand = serializers.CharField(help_text="Exact brand name (case-insensitive).")


class SmartSubstituteQuerySerializer(LocationQuerySerializer):
    brand = serializers.CharField(help_text="Exact brand name (case-insensitive).")
    emergency = serializers.BooleanField(
        default=False, help_text="Only include 24x7 pharmacies."
    )


class MedicineSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="Matches brand or generic name. Empty returns the paginated catalogue.",
    )
