from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Pharmacy
from accounts.views import get_role
from .utils import haversine, bounding_box_filter
from pharmaconnect.api import LocationQuerySerializer, paginate
from inventory.models import Inventory
from ml_service.ai_restock_service import generate_ai_restock


# ----------- API: Nearest Pharmacies (Already Working) -----------
class NearestPharmacyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[LocationQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        params = LocationQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        user_lat = params.validated_data['lat']
        user_lon = params.validated_data['lon']
        radius_km = params.validated_data['radius_km']

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
        page, envelope = paginate(self, request, result)
        return Response({**envelope, "results": page})


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