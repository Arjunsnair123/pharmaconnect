from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from pharmacies.models import Pharmacy
from medicines.models import Medicine
from .models import Inventory
from accounts.views import get_role
from pharmacies.utils import haversine, bounding_box_filter
from pharmaconnect.api import AvailabilityQuerySerializer, paginate
from ml_service.models import SearchLog


# ---------------- MEDICINE AVAILABILITY API ----------------

class AvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(parameters=[AvailabilityQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        params = AvailabilityQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        med_name = params.validated_data['medicine']
        user_lat = params.validated_data['lat']
        user_lon = params.validated_data['lon']
        radius_km = params.validated_data['radius_km']
        emergency = params.validated_data['emergency']

        medicine = Medicine.objects.filter(brand_name__iexact=med_name).first()
        if medicine is None:
            return Response({"error": "Medicine not found"}, status=404)

        stocks = Inventory.objects.select_related("pharmacy").filter(
            medicine=medicine,
            quantity__gt=0,
            **bounding_box_filter(user_lat, user_lon, radius_km, prefix="pharmacy__")
        )
        if emergency:
            stocks = stocks.filter(pharmacy__is_24x7=True)

        result = []
        nearest_pharmacy = None
        nearest_distance = float('inf')

        for stock in stocks:
            p = stock.pharmacy

            dist = haversine(user_lat, user_lon, p.latitude, p.longitude)
            if dist > radius_km:
                continue

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

        # Save search log
        if request.user.is_authenticated and nearest_pharmacy:
            SearchLog.objects.create(
                user=request.user,
                medicine=med_name,
                latitude=user_lat,
                longitude=user_lon,
                nearest_pharmacy=nearest_pharmacy
            )

        result.sort(key=lambda x: x["distance_km"])

        page, envelope = paginate(self, request, result)

        return Response({
            "nearest_pharmacy": nearest_pharmacy.name if nearest_pharmacy else None,
            **envelope,
            "results": page
        })


# ---------------- PHARMACY INVENTORY MANAGEMENT ----------------

@login_required
def pharmacy_inventory(request):
    # The pharmacy is always derived from the logged-in user, never from the
    # request, so one pharmacy cannot read or edit another's stock.
    if get_role(request.user) != "PHARMACY":
        return HttpResponseForbidden("Pharmacy account required.")

    pharmacy = getattr(request.user, "pharmacy", None)
    if pharmacy is None:
        return HttpResponseForbidden("No pharmacy is linked to this account.")

    if request.method == "POST":
        try:
            med_id = request.POST.get("medicine")
            qty = int(request.POST.get("quantity", 0))
            if qty < 0:
                raise ValueError("Quantity cannot be negative")

            medicine = Medicine.objects.get(id=med_id)

            
            inventory, created = Inventory.objects.get_or_create(
                pharmacy=pharmacy,
                medicine=medicine,
                defaults={"quantity": qty}
            )

            # If already exists → update quantity
            if not created:
                inventory.quantity = qty
                inventory.save()

        except Exception as e:
            print("Error:", e)

        return redirect("pharmacy_inventory")

    inventories = Inventory.objects.filter(pharmacy=pharmacy) \
                    .select_related("medicine") \
                    .order_by("medicine__brand_name")

    medicines = Medicine.objects.all().order_by("brand_name")

    return render(request, "pharmacy_inventory.html", {
        "inventories": inventories,
        "medicines": medicines,
        "pharmacy": pharmacy
    })