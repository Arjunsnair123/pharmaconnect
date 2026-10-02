from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Pharmacy
from accounts.views import get_role
from .utils import haversine, bounding_box_filter, get_radius_km
from inventory.models import Inventory
from ml_service.ai_restock_service import generate_ai_restock


# ----------- API: Nearest Pharmacies (Already Working) -----------
class NearestPharmacyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_lat = float(request.GET.get('lat'))
        user_lon = float(request.GET.get('lon'))

        radius_km = get_radius_km(request)

        pharmacies = Pharmacy.objects.filter(
            **bounding_box_filter(user_lat, user_lon, radius_km)
        )
        result = []

        for p in pharmacies:
            distance = haversine(user_lat, user_lon, p.latitude, p.longitude)
            if distance > radius_km:
                continue
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
    if get_role(request.user) != "PHARMACY":
        return redirect("login")

    # Pharmacies are created and linked to a user by an admin; never invent
    # one with placeholder coordinates just because the page was opened.
    pharmacy = getattr(request.user, "pharmacy", None)
    if pharmacy is None:
        return HttpResponseForbidden("No pharmacy is linked to this account.")

    inventory = Inventory.objects.filter(pharmacy=pharmacy).select_related("medicine")
    
    ai_data = generate_ai_restock()

    pharmacy_ai = ai_data["pharmacy_allocation"].get(pharmacy.id, {})

    return render(request, "pharmacies/dashboard.html", {
    "pharmacy": pharmacy,
    "inventory": inventory,
    "ai_restock": pharmacy_ai
})