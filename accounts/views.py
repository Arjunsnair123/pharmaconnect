from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Profile


def get_role(user):
    """Role for a user, tolerating accounts that have no Profile row
    (e.g. superusers made with createsuperuser)."""
    profile = Profile.objects.filter(user=user).first()
    if profile:
        return profile.role
    if user.is_staff:
        return 'ADMIN'
    return Profile.objects.create(user=user, role='PATIENT').role


def redirect_for_role(user):
    role = get_role(user)
    if role == 'PHARMACY':
        return redirect('pharmacy_dashboard')
    if role == 'ADMIN':
        return redirect('admin:index')
    return redirect('patient_dashboard')


def login_view(request):
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get('username', ''),
            password=request.POST.get('password', '')
        )
        if user:
            login(request, user)
            return redirect_for_role(user)
        error = "Invalid username or password."

    return render(request, 'accounts/login.html', {"error": error})


def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return redirect_for_role(request.user)


def register_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error = "Username and password are required."
        elif User.objects.filter(username=username).exists():
            error = "That username is already taken."
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            # Self-registration is always PATIENT. Any "role" sent by the
            # client is ignored; pharmacy/admin accounts are set up in /admin/.
            Profile.objects.create(user=user, role='PATIENT')
            return redirect('login')

    return render(request, 'accounts/register.html', {"error": error})


def logout_view(request):
    logout(request)
    return redirect('login')
