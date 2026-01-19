from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Pharmacy
from .utils import haversine

class NearestPharmacyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))

        pharmacies = Pharmacy.objects.all()
        result = []

        for p in pharmacies:
            distance = haversine(user_lat, user_lon, p.latitude, p.longitude)
            result.append({
                "name": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "is_24x7": p.is_24x7,
                "distance_km": round(distance, 2)
            })

        result.sort(key=lambda x: x["distance_km"])
        return Response(result)
