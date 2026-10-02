from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from pharmacies.models import Pharmacy


class RegistrationTests(TestCase):
    def test_role_and_pharmacy_from_post_are_ignored(self):
        owner = User.objects.create_user("owner", password="pw")
        pharmacy = Pharmacy.objects.create(
            user=owner, name="P1", address="a", latitude=10.0, longitude=76.0
        )

        self.client.post(reverse("register"), {
            "username": "mallory", "email": "m@example.com", "password": "pw12345!",
            "role": "ADMIN", "pharmacy_id": pharmacy.id,
        })

        profile = Profile.objects.get(user__username="mallory")
        self.assertEqual(profile.role, "PATIENT")
        pharmacy.refresh_from_db()
        self.assertEqual(pharmacy.user, owner)

    def test_duplicate_username_shows_error(self):
        User.objects.create_user("taken", password="pw")
        response = self.client.post(reverse("register"), {
            "username": "taken", "email": "t@example.com", "password": "pw12345!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already taken")


class LoginTests(TestCase):
    def test_failed_login_shows_error(self):
        response = self.client.post(reverse("login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_admin_role_redirects_to_django_admin(self):
        user = User.objects.create_user("boss", password="pw", is_staff=True)
        Profile.objects.create(user=user, role="ADMIN")
        response = self.client.post(reverse("login"), {"username": "boss", "password": "pw"})
        self.assertRedirects(response, reverse("admin:index"), fetch_redirect_response=False)

    def test_user_without_profile_can_log_in(self):
        User.objects.create_user("noprofile", password="pw")
        response = self.client.post(reverse("login"), {"username": "noprofile", "password": "pw"})
        self.assertRedirects(response, reverse("patient_dashboard"), fetch_redirect_response=False)
        self.assertEqual(Profile.objects.get(user__username="noprofile").role, "PATIENT")
