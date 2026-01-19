from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def patient_dashboard(request):
    return render(request, 'dashboard/patient_dashboard.html')
@login_required
def live_map(request):
    return render(request, 'dashboard/live_map.html')