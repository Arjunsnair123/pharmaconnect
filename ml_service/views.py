from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from ml.demand_forecast import ModelNotTrained, predict_next_week_demand
from ml_service.spatial_allocator import allocate_weekly_stock

class WeeklyForecastView(APIView):
    # Exposes the allocation for every pharmacy, so staff only.
    permission_classes = [IsAdminUser]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        try:
            total_weekly_demand, daily_predictions = predict_next_week_demand()
        except ModelNotTrained as exc:
            return Response({"error": str(exc)}, status=503)
        spatial_distribution = allocate_weekly_stock(total_weekly_demand)

        return Response({
            "total_area_demand_next_week": total_weekly_demand,
            "daily_prediction": daily_predictions.tolist(),
            "pharmacy_wise_allocation": spatial_distribution
        })
