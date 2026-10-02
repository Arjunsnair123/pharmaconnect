from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.permissions import AllowAny
from medicines.models import Medicine

from .models import Medicine
from .serializers import MedicineSerializer
from inventory.models import Inventory
from pharmacies.utils import haversine, bounding_box_filter
from pharmaconnect.api import (
    BrandQuerySerializer, MedicineSearchQuerySerializer,
    SmartSubstituteQuerySerializer, paginate,
)


class MedicineSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[MedicineSearchQuerySerializer], responses=MedicineSerializer(many=True))
    def get(self, request):
        params = MedicineSearchQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        query = params.validated_data['q']

        medicines = Medicine.objects.filter(
            Q(brand_name__icontains=query) |
            Q(generic_name__icontains=query)
        ).order_by('brand_name', 'id')

        page, envelope = paginate(self, request, medicines)
        return Response({**envelope, "results": MedicineSerializer(page, many=True).data})


class SubstituteSuggestionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[BrandQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        params = BrandQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        brand = params.validated_data['brand']

        medicine = Medicine.objects.filter(brand_name__iexact=brand).first()
        if medicine is None:
            return Response({"error": "Medicine not found"}, status=404)

        substitutes = Medicine.objects.filter(
            generic_name=medicine.generic_name,
            dosage_form=medicine.dosage_form
        ).exclude(id=medicine.id).order_by('brand_name', 'id')

        page, envelope = paginate(self, request, substitutes)

        return Response({
            "original": MedicineSerializer(medicine).data,
            **envelope,
            "substitutes": MedicineSerializer(page, many=True).data
        })


class SmartSubstituteView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[SmartSubstituteQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        params = SmartSubstituteQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        brand = params.validated_data['brand']
        lat = params.validated_data['lat']
        lon = params.validated_data['lon']
        radius_km = params.validated_data['radius_km']
        emergency = params.validated_data['emergency']

        target = Medicine.objects.filter(brand_name__iexact=brand).first()
        if target is None:
            return Response({"error": "Medicine not found"}, status=404)

        candidates = Medicine.objects.filter(
        generic_name=target.generic_name,
        dosage_form=target.dosage_form
        ).exclude(id=target.id)

        # One query for every candidate's stock (was one query per medicine
        # plus one per stock row for its pharmacy).
        stocks = Inventory.objects.select_related("pharmacy", "medicine").filter(
            medicine__in=candidates,
            quantity__gt=0,
            **bounding_box_filter(lat, lon, radius_km, prefix="pharmacy__")
        )
        if emergency:
            stocks = stocks.filter(pharmacy__is_24x7=True)

        results = []

        for stock in stocks:
            p = stock.pharmacy
            med = stock.medicine

            dist = haversine(lat, lon, p.latitude, p.longitude)
            if dist > radius_km:
                continue

            results.append({
                "medicine": med.brand_name,
                "generic": med.generic_name,
                "strength": med.strength,
                "pharmacy": p.name,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "distance_km": round(dist, 2),
                "quantity": stock.quantity,
                "is_24x7": p.is_24x7
            })

        results.sort(key=lambda x: x["distance_km"])

        page, envelope = paginate(self, request, results)

        return Response({
            "requested": target.brand_name,
            "generic": target.generic_name,
            **envelope,
            "nearest_substitutes": page
        })

class MedicineSuggestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("q", str, description="At least 2 characters.")],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    def get(self, request):
        q = request.GET.get("q", "").strip()

        if len(q) < 2:
            return Response([])

        medicines = Medicine.objects.filter(
            brand_name__icontains=q
        ).values_list("brand_name", flat=True)[:8]

        return Response(list(medicines))