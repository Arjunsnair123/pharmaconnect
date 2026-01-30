from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication

from pharmacies.models import Pharmacy
from medicines.models import Medicine
from .models import Inventory
from pharmacies.utils import haversine
from ml_service.models import SearchLog


class AvailabilityView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        med_name = request.GET.get('medicine')
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        emergency = request.GET.get('emergency', 'false').lower() == 'true'

        if not med_name or not lat or not lon:
            return Response({"error": "Missing medicine or location"}, status=400)

        try:
            user_lat = float(lat)
            user_lon = float(lon)
        except ValueError:
            return Response({"error": "Invalid coordinates"}, status=400)

        try:
            medicine = Medicine.objects.get(brand_name__iexact=med_name)
        except Medicine.DoesNotExist:
            return Response({"error": "Medicine not found"}, status=404)

        stocks = Inventory.objects.select_related("pharmacy").filter(
            medicine=medicine,
            quantity__gt=0
        )

        result = []
        nearest_pharmacy = None
        nearest_distance = float('inf')

        for stock in stocks:
            p = stock.pharmacy

            if emergency and not p.is_24x7:
                continue

            dist = haversine(user_lat, user_lon, p.latitude, p.longitude)

            if dist < nearest_distance:
                nearest_distance = dist
                nearest_pharmacy = p

            result.append({
                "pharmacy": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "distance_km": round(dist, 2),
                "quantity": stock.quantity,
                "is_24x7": p.is_24x7
            })

        if request.user.is_authenticated and nearest_pharmacy:
            SearchLog.objects.create(
                user=request.user,
                medicine=med_name,
                latitude=user_lat,
                longitude=user_lon,
                nearest_pharmacy=nearest_pharmacy
            )

        result.sort(key=lambda x: x["distance_km"])

        return Response({
            "nearest_pharmacy": nearest_pharmacy.name if nearest_pharmacy else None,
            "results": result
        })


# ---------------- PHARMACY INVENTORY MANAGEMENT ----------------

@login_required
def pharmacy_inventory(request):
    pharmacy = Pharmacy.objects.get(user=request.user)

    if request.method == "POST":
        med_id = request.POST["medicine"]
        qty = int(request.POST["quantity"])

        medicine = Medicine.objects.get(id=med_id)
        inventory, created = Inventory.objects.get_or_create(
            pharmacy=pharmacy,
            medicine=medicine
        )
        inventory.quantity = qty
        inventory.save()
        return redirect("pharmacy_inventory")

    inventories = Inventory.objects.filter(pharmacy=pharmacy)\
                    .select_related("medicine")\
                    .order_by("medicine__brand_name")

    medicines = Medicine.objects.all().order_by("brand_name")

    return render(request, "pharmacy_inventory.html", {
        "inventories": inventories,
        "medicines": medicines,
        "pharmacy": pharmacy
    })