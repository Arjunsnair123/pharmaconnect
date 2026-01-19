from django.urls import path
from .views import AvailabilityView

urlpatterns = [
    path('availability/', AvailabilityView.as_view()),
]
