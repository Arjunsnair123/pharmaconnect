from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
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
            return redirect('patient_dashboard')
    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == "POST":
        user = User.objects.create_user(
            username=request.POST['username'],
            email=request.POST['email'],
            password=request.POST['password']
        )
        Profile.objects.create(user=user, role=request.POST['role'])
        return redirect('login')
    return render(request, 'accounts/register.html')

def logout_view(request):
    logout(request)
    return redirect('login')
