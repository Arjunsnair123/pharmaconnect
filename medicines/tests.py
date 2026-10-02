from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from inventory.models import Inventory
from medicines.models import Medicine
from pharmacies.models import Pharmacy


def make_medicine(brand, generic="Paracetamol", **extra):
    fields = dict(
        composition=generic, strength="500mg", dosage_form="tablet", category="analgesic"
    )
    fields.update(extra)
    return Medicine.objects.create(brand_name=brand, generic_name=generic, **fields)


class QueryValidationTests(TestCase):
    """Bad or missing query params must be a 400, never a 500."""

    def setUp(self):
        self.client = APIClient()
        make_medicine("Dolo 650")

    def assert_400(self, url, params, field):
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn(field, response.json())

    def test_nearest_requires_coordinates(self):
        self.assert_400("/api/pharmacies/nearest/", {}, "lat")

    def test_nearest_rejects_non_numeric_and_out_of_range(self):
        self.assert_400("/api/pharmacies/nearest/", {"lat": "abc", "lon": 76}, "lat")
        self.assert_400("/api/pharmacies/nearest/", {"lat": 10, "lon": 500}, "lon")
        self.assert_400("/api/pharmacies/nearest/", {"lat": "nan", "lon": 76}, "lat")
        self.assert_400("/api/pharmacies/nearest/", {"lat": 10, "lon": 76, "radius_km": -1}, "radius_km")

    def test_smart_substitutes_requires_brand_and_coordinates(self):
        self.assert_400("/api/medicines/smart-substitutes/", {"lat": 10, "lon": 76}, "brand")
        self.assert_400("/api/medicines/smart-substitutes/", {"brand": "Dolo 650"}, "lat")

    def test_availability_requires_medicine(self):
        self.client.force_authenticate(User.objects.create_user("u", password="pw"))
        self.assert_400("/api/inventory/availability/", {"lat": 10, "lon": 76}, "medicine")
        self.assert_400(
            "/api/inventory/availability/", {"medicine": "Dolo 650", "lat": "x", "lon": 76}, "lat"
        )


class MedicineSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        for i in range(25):
            make_medicine(f"Brand {i:02d}")

    def test_empty_query_is_paginated_not_the_whole_table(self):
        body = self.client.get("/api/medicines/search/").json()
        self.assertEqual(body["count"], 25)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])

    def test_query_filters_results(self):
        body = self.client.get("/api/medicines/search/", {"q": "brand 07"}).json()
        self.assertEqual([m["brand_name"] for m in body["results"]], ["Brand 07"])


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("u", password="pw")
        make_medicine("Dolo 650")
        self.params = {"medicine": "Dolo 650", "lat": 10, "lon": 76}

    def test_availability_requires_authentication(self):
        response = self.client.get("/api/inventory/availability/", self.params)
        self.assertEqual(response.status_code, 401)

    def test_availability_accepts_jwt(self):
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/inventory/availability/", self.params)
        self.assertEqual(response.status_code, 200)

    def test_availability_accepts_session(self):
        self.client.login(username="u", password="pw")
        response = self.client.get("/api/inventory/availability/", self.params)
        self.assertEqual(response.status_code, 200)

    def test_forecast_is_staff_only(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/ml/forecast/").status_code, 403)

    def test_api_schema_is_served(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)


class SubstituteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dolo = make_medicine("Dolo 650")
        self.calpol = make_medicine("Calpol")
        self.crocin = make_medicine("Crocin")
        make_medicine("Calpol Syrup", dosage_form="syrup")   # same generic, other form
        make_medicine("Brufen", generic="Ibuprofen")         # other generic

    def test_substitutes_share_generic_and_dosage_form(self):
        body = self.client.get("/api/medicines/substitutes/", {"brand": "dolo 650"}).json()

        self.assertEqual(body["original"]["brand_name"], "Dolo 650")
        self.assertEqual([m["brand_name"] for m in body["substitutes"]], ["Calpol", "Crocin"])

    def test_unknown_brand_is_404(self):
        response = self.client.get("/api/medicines/substitutes/", {"brand": "Nope"})
        self.assertEqual(response.status_code, 404)

    def test_smart_substitutes_lists_stocked_alternatives_nearest_first(self):
        near = self.make_pharmacy("near", 10.81, is_24x7=False)
        further = self.make_pharmacy("further", 10.845, is_24x7=True)
        Inventory.objects.create(pharmacy=further, medicine=self.calpol, quantity=4)
        Inventory.objects.create(pharmacy=near, medicine=self.crocin, quantity=2)
        Inventory.objects.create(pharmacy=near, medicine=self.calpol, quantity=0)   # out of stock
        Inventory.objects.create(pharmacy=near, medicine=self.dolo, quantity=9)     # the original

        params = {"brand": "Dolo 650", "lat": 10.80, "lon": 76.64}
        body = self.client.get("/api/medicines/smart-substitutes/", params).json()

        self.assertEqual(
            [(r["medicine"], r["pharmacy"]) for r in body["nearest_substitutes"]],
            [("Crocin", "near"), ("Calpol", "further")],
        )

        emergency = self.client.get(
            "/api/medicines/smart-substitutes/", {**params, "emergency": "true"}
        ).json()
        self.assertEqual(
            [(r["medicine"], r["pharmacy"]) for r in emergency["nearest_substitutes"]],
            [("Calpol", "further")],
        )

    def make_pharmacy(self, name, lat, **extra):
        user = User.objects.create_user(f"{name}-owner", password="pw")
        return Pharmacy.objects.create(
            user=user, name=name, address="x", latitude=lat, longitude=76.64, **extra
        )
