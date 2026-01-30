from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.permissions import AllowAny
from medicines.models import Medicine

from .models import Medicine
from .serializers import MedicineSerializer
from inventory.models import Inventory
from pharmacies.utils import haversine


class MedicineSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.GET.get('q', '')
        medicines = Medicine.objects.filter(
            Q(brand_name__icontains=query) |
            Q(generic_name__icontains=query)
        )
        serializer = MedicineSerializer(medicines, many=True)
        return Response(serializer.data)


class SubstituteSuggestionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        brand = request.GET.get('brand')

        try:
            medicine = Medicine.objects.get(brand_name__iexact=brand)
        except Medicine.DoesNotExist:
            return Response({"error": "Medicine not found"}, status=404)

        substitutes = Medicine.objects.filter(
            generic_name=medicine.generic_name,
            dosage_form=medicine.dosage_form
        ).exclude(id=medicine.id)

        return Response({
            "original": MedicineSerializer(medicine).data,
            "substitutes": MedicineSerializer(substitutes, many=True).data
        })


class SmartSubstituteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        brand = request.GET.get('brand')
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
        emergency = request.GET.get('emergency', 'false').lower() == 'true'

        try:
            target = Medicine.objects.get(brand_name__iexact=brand)
        except Medicine.DoesNotExist:
            return Response({"error": "Medicine not found"}, status=404)

        candidates = Medicine.objects.filter(
        generic_name=target.generic_name,
        dosage_form=target.dosage_form
        ).exclude(id=target.id)


        results = []

        for med in candidates:
            stocks = Inventory.objects.filter(medicine=med, quantity__gt=0)

            for stock in stocks:
                p = stock.pharmacy

                if emergency and not p.is_24x7:
                    continue

                dist = haversine(lat, lon, p.latitude, p.longitude)

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

        return Response({
            "requested": target.brand_name,
            "generic": target.generic_name,
            "nearest_substitutes": results
        })

class MedicineSuggestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.GET.get("q", "").strip()

        if len(q) < 2:
            return Response([])

        medicines = Medicine.objects.filter(
            brand_name__icontains=q
        ).values_list("brand_name", flat=True)[:8]

        return Response(list(medicines))