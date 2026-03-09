from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from pharmacies.models import Pharmacy
from .models import Profile

def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            role = user.profile.role

            if role == 'PHARMACY':
                return redirect('pharmacy_dashboard')
            elif role == 'ADMIN':
                return redirect('admin_dashboard')
            else:
                return redirect('patient_dashboard')

    return render(request, 'accounts/login.html')

from django.shortcuts import redirect

def home_redirect(request):

    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.profile.role == "PHARMACY":
        return redirect("/api/pharmacies/dashboard/")

    if request.user.profile.role == "PATIENT":
        return redirect("/dashboard/patient/")

    return redirect("login")


from pharmacies.models import Pharmacy

def register_view(request):
    if request.method == "POST":
        user = User.objects.create_user(
            username=request.POST['username'],
            email=request.POST['email'],
            password=request.POST['password']
        )

        role = request.POST['role']
        profile = Profile.objects.create(user=user, role=role)

        if role == "PHARMACY":
            pharmacy_id = request.POST['pharmacy_id']
            profile.pharmacy = Pharmacy.objects.get(id=pharmacy_id)
            profile.save()

        return redirect('login')

    pharmacies = Pharmacy.objects.all()
    return render(request, 'accounts/register.html', {"pharmacies": pharmacies})



def logout_view(request):
    logout(request)
    return redirect('login')
