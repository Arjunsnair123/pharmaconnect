from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from pharmacies.models import Pharmacy
from medicines.models import Medicine
from .models import Inventory
from pharmacies.utils import haversine

class AvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        med_name = request.GET.get('medicine')
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))
        emergency = request.GET.get('emergency', 'false').lower() == 'true'

        try:
            medicine = Medicine.objects.get(brand_name__iexact=med_name)
        except Medicine.DoesNotExist:
            return Response({"error": "Medicine not found"}, status=404)

        stocks = Inventory.objects.filter(medicine=medicine, quantity__gt=0)
        result = []

        for stock in stocks:
            p = stock.pharmacy
            if emergency and not p.is_24x7:
                continue

            dist = haversine(user_lat, user_lon, p.latitude, p.longitude)

            result.append({
                "pharmacy": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "distance_km": round(dist, 2),
                "quantity": stock.quantity,
                "is_24x7": p.is_24x7
            })

        result.sort(key=lambda x: x["distance_km"])
        return Response(result)
