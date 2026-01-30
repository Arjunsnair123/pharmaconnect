from django.urls import path
from .views import NearestPharmacyView, pharmacy_dashboard

urlpatterns = [
    path('nearest/', NearestPharmacyView.as_view()),
    path('dashboard/', pharmacy_dashboard, name='pharmacy_dashboard'),
]
