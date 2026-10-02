from django.urls import path
from .views import WeeklyForecastView

urlpatterns = [
    path('forecast/', WeeklyForecastView.as_view(), name='weekly_forecast'),
]
