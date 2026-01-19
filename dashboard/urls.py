from django.urls import path
from .views import patient_dashboard, live_map

urlpatterns = [
    path('patient/', patient_dashboard, name='patient_dashboard'),
    path('map/', live_map, name='live_map'),
]
