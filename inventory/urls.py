from django.urls import path
from .views import AvailabilityView, pharmacy_inventory

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="availability"),
    path("pharmacy/inventory/", pharmacy_inventory, name="pharmacy_inventory"),
   
]
