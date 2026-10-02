from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from inventory.models import Inventory
from medicines.models import Medicine
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
