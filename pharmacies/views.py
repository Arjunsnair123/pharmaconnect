from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Pharmacy
from .utils import haversine
from inventory.models import Inventory


# ----------- API: Nearest Pharmacies (Already Working) -----------
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


# ----------- WEB: Pharmacy Dashboard -----------
@login_required
def pharmacy_dashboard(request):
    if request.user.profile.role != "PHARMACY":
        return redirect("login")

    pharmacy, created = Pharmacy.objects.get_or_create(
    user=request.user,
    defaults={
        "name": f"{request.user.username} Medicals",
        "address": "Address not set",
        "latitude": 10.8219,
        "longitude": 76.6432,
        "is_24x7": False
    }
)

    inventory = Inventory.objects.filter(pharmacy=pharmacy)

    context = {
        "pharmacy": pharmacy,
        "inventory": inventory,
    }

    return render(request, "pharmacies/dashboard.html", context)
