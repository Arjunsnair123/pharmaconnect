from django.urls import path
from .views import NearestPharmacyView

urlpatterns = [
    path('nearest/', NearestPharmacyView.as_view()),
]
