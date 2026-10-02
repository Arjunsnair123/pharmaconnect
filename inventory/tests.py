from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Profile
from inventory.models import Inventory
from medicines.models import Medicine
from ml_service.models import SearchLog
from pharmacies.models import Pharmacy


class PharmacyInventoryPermissionTests(TestCase):
    def setUp(self):
        self.medicine = Medicine.objects.create(
            brand_name="Dolo 650", generic_name="Paracetamol", composition="Paracetamol",
            strength="650mg", dosage_form="tablet", category="analgesic",
        )
        self.user_a, self.pharmacy_a = self.make_pharmacy("a")
        self.user_b, self.pharmacy_b = self.make_pharmacy("b")
        Inventory.objects.create(pharmacy=self.pharmacy_b, medicine=self.medicine, quantity=5)

    def make_pharmacy(self, name):
        user = User.objects.create_user(name, password="pw")
        Profile.objects.create(user=user, role="PHARMACY")
        pharmacy = Pharmacy.objects.create(
            user=user, name=f"Pharmacy {name}", address="x", latitude=10.0, longitude=76.0
        )
        return user, pharmacy

    def test_pharmacy_only_sees_and_edits_own_stock(self):
        self.client.force_login(self.user_a)
        url = reverse("pharmacy_inventory")

        response = self.client.get(url)
        self.assertEqual(list(response.context["inventories"]), [])

        # Even if the client names another pharmacy, the write lands on its own.
        self.client.post(url, {
            "medicine": self.medicine.id, "quantity": 99, "pharmacy": self.pharmacy_b.id,
        })
        self.assertEqual(Inventory.objects.get(pharmacy=self.pharmacy_b).quantity, 5)
        self.assertEqual(Inventory.objects.get(pharmacy=self.pharmacy_a).quantity, 99)

    def test_patient_is_forbidden(self):
        patient = User.objects.create_user("pat", password="pw")
        Profile.objects.create(user=patient, role="PATIENT")
        self.client.force_login(patient)
        self.assertEqual(self.client.get(reverse("pharmacy_inventory")).status_code, 403)

    def test_pharmacy_role_without_linked_pharmacy_is_forbidden(self):
        user = User.objects.create_user("orphan", password="pw")
        Profile.objects.create(user=user, role="PHARMACY")
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("pharmacy_inventory"), {
            "medicine": self.medicine.id, "quantity": 1,
        }).status_code, 403)


class InventoryConstraintTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("p", password="pw")
        self.pharmacy = Pharmacy.objects.create(
            user=user, name="P", address="x", latitude=10.0, longitude=76.0
        )
        self.medicine = Medicine.objects.create(
            brand_name="Dolo 650", generic_name="Paracetamol", composition="Paracetamol",
            strength="650mg", dosage_form="tablet", category="analgesic",
        )

    def test_duplicate_pharmacy_medicine_row_is_rejected(self):
        Inventory.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inventory.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=2)

    def test_negative_quantity_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inventory.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=-1)


class AvailabilitySearchTests(TestCase):
    """Search point is (10.80, 76.64); 'near' is ~1 km away, 'further' ~5 km."""

    URL = "/api/inventory/availability/"

    def setUp(self):
        self.client = APIClient()
        self.patient = User.objects.create_user("patient", password="pw")
        self.client.force_authenticate(self.patient)

        self.dolo = Medicine.objects.create(
            brand_name="Dolo 650", generic_name="Paracetamol", composition="Paracetamol",
            strength="650mg", dosage_form="tablet", category="analgesic",
        )
        self.near = self.make_pharmacy("near", 10.81, 76.64, is_24x7=False)
        self.further = self.make_pharmacy("further", 10.845, 76.64, is_24x7=True)
        self.empty = self.make_pharmacy("empty", 10.80, 76.64, is_24x7=True)

        Inventory.objects.create(pharmacy=self.near, medicine=self.dolo, quantity=10)
        Inventory.objects.create(pharmacy=self.further, medicine=self.dolo, quantity=3)
        Inventory.objects.create(pharmacy=self.empty, medicine=self.dolo, quantity=0)

    def make_pharmacy(self, name, lat, lon, **extra):
        user = User.objects.create_user(f"{name}-owner", password="pw")
        return Pharmacy.objects.create(
            user=user, name=name, address="x", latitude=lat, longitude=lon, **extra
        )

    def search(self, **params):
        query = {"medicine": "Dolo 650", "lat": 10.80, "lon": 76.64, **params}
        return self.client.get(self.URL, query)

    def test_returns_stocked_pharmacies_nearest_first(self):
        body = self.search().json()

        self.assertEqual([r["pharmacy"] for r in body["results"]], ["near", "further"])
        self.assertEqual(body["nearest_pharmacy"], "near")
        self.assertEqual(body["results"][0]["quantity"], 10)
        self.assertLess(body["results"][0]["distance_km"], body["results"][1]["distance_km"])

    def test_out_of_stock_pharmacy_is_excluded_even_when_closest(self):
        # 'empty' sits exactly on the search point but has quantity 0.
        names = [r["pharmacy"] for r in self.search().json()["results"]]
        self.assertNotIn("empty", names)

    def test_medicine_out_of_stock_everywhere_gives_empty_results(self):
        Inventory.objects.update(quantity=0)

        response = self.search()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
        self.assertIsNone(response.json()["nearest_pharmacy"])
        self.assertFalse(SearchLog.objects.exists())

    def test_emergency_mode_returns_only_24x7_pharmacies(self):
        body = self.search(emergency="true").json()

        self.assertEqual([r["pharmacy"] for r in body["results"]], ["further"])
        self.assertEqual(body["nearest_pharmacy"], "further")

    def test_medicine_name_is_case_insensitive(self):
        self.assertEqual(self.search(medicine="dolo 650").json()["count"], 2)

    def test_unknown_medicine_is_404(self):
        self.assertEqual(self.search(medicine="Nonexistent").status_code, 404)

    def test_search_is_logged_against_nearest_pharmacy(self):
        self.search()

        log = SearchLog.objects.get()
        self.assertEqual(log.user, self.patient)
        self.assertEqual(log.nearest_pharmacy, self.near)
        self.assertEqual(log.medicine, "Dolo 650")
