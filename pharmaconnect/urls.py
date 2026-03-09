from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.views import home_redirect

urlpatterns = [
    path('', home_redirect, name="home"),
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('dashboard/', include('dashboard.urls')),


    # APIs
    path('api/medicines/', include('medicines.urls')),
    path('api/pharmacies/', include('pharmacies.urls')),
    path('api/inventory/', include('inventory.urls')),
]
