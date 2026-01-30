from rest_framework.views import APIView
from rest_framework.response import Response
from ml.demand_forecast import predict_next_week_demand
from ml_service.spatial_allocator import allocate_weekly_stock

class WeeklyForecastView(APIView):
    def get(self, request):
        total_weekly_demand, daily_predictions = predict_next_week_demand()
        spatial_distribution = allocate_weekly_stock(total_weekly_demand)

        return Response({
            "total_area_demand_next_week": total_weekly_demand,
            "daily_prediction": daily_predictions.tolist(),
            "pharmacy_wise_allocation": spatial_distribution
        })
