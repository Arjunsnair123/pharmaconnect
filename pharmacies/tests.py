from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Profile
from pharmacies.models import Pharmacy
from pharmacies.utils import bounding_box_filter


def make_pharmacy(username, lat, lon, **extra):
    user = User.objects.create_user(username, password="pw")
    return Pharmacy.objects.create(
        user=user, name=f"{username} Medicals", address="x", latitude=lat, longitude=lon, **extra
    )


class NearestPharmacyRadiusTests(TestCase):
    def setUp(self):
        make_pharmacy("near", 10.80, 76.64)      # ~2 km from the search point
        make_pharmacy("far", 12.97, 77.59)       # Bengaluru, ~260 km away

    def test_default_radius_excludes_distant_pharmacies(self):
        response = self.client.get("/api/pharmacies/nearest/", {"lat": 10.82, "lon": 76.64})
        self.assertEqual([p["name"] for p in response.json()], ["near Medicals"])

    def test_radius_km_param_widens_search(self):
        response = self.client.get(
            "/api/pharmacies/nearest/", {"lat": 10.82, "lon": 76.64, "radius_km": 400}
        )
        self.assertEqual(
            [p["name"] for p in response.json()], ["near Medicals", "far Medicals"]
        )

    def test_bounding_box_skips_longitude_bound_across_antimeridian(self):
        filters = bounding_box_filter(0, 179.9, 50)
        self.assertNotIn("longitude__gte", filters)


class PharmacyOwnershipTests(TestCase):
    def test_user_cannot_own_two_pharmacies(self):
        pharmacy = make_pharmacy("owner", 10.0, 76.0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pharmacy.objects.create(
                user=pharmacy.user, name="Second", address="x", latitude=10.0, longitude=76.0
            )

    def test_dashboard_does_not_create_a_pharmacy_for_unlinked_user(self):
        user = User.objects.create_user("orphan", password="pw")
        Profile.objects.create(user=user, role="PHARMACY")
        self.client.force_login(user)

        response = self.client.get("/api/pharmacies/dashboard/")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Pharmacy.objects.exists())
