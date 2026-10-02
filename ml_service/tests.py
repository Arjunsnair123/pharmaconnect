import os
import sys
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from accounts.models import Profile
from inventory.models import Inventory
from medicines.models import Medicine
from ml import demand_forecast
from ml_service.ai_restock_service import generate_ai_restock
from ml_service.models import SearchLog
from ml_service.spatial_allocator import allocate_weekly_stock
from pharmacies.models import Pharmacy


class RestockTestCase(TestCase):
    """Fixtures plus a model path isolated from the developer's real one."""

    def setUp(self):
        cache.clear()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(
            demand_forecast, "MODEL_PATH", os.path.join(tmp.name, "model.joblib")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.user = User.objects.create_user("pharm", password="pw")
        Profile.objects.create(user=self.user, role="PHARMACY")
        self.pharmacy = Pharmacy.objects.create(
            user=self.user, name="P", address="x", latitude=10.0, longitude=76.0
        )
        self.medicine = Medicine.objects.create(
            brand_name="Dolo 650", generic_name="Paracetamol", composition="Paracetamol",
            strength="650mg", dosage_form="tablet", category="analgesic",
        )

    def log_search(self, pharmacy):
        SearchLog.objects.create(
            user=self.user, medicine="Dolo 650", latitude=10.0, longitude=76.0,
            nearest_pharmacy=pharmacy,
        )


class SpatialAllocatorTests(RestockTestCase):
    def test_search_with_no_nearest_pharmacy_does_not_crash(self):
        self.log_search(self.pharmacy)
        self.log_search(None)

        allocation = allocate_weekly_stock(100)

        # Half the searches for the medicine hit this pharmacy.
        self.assertEqual(allocation, {self.pharmacy.id: {"Dolo 650": 50}})

    def test_no_searches_gives_empty_allocation(self):
        self.assertEqual(allocate_weekly_stock(100), {})


class RestockServiceTests(RestockTestCase):
    def test_dashboard_loads_without_a_trained_model(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/pharmacies/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["ai_restock"], {})

    def test_request_path_does_not_train_or_import_matplotlib(self):
        call_command("train_demand_model", stdout=open(os.devnull, "w"))
        self.log_search(self.pharmacy)
        sys.modules.pop("matplotlib.pyplot", None)

        with mock.patch.object(demand_forecast, "train_and_save") as train:
            self.client.force_login(self.user)
            response = self.client.get("/api/pharmacies/dashboard/")

        self.assertEqual(response.status_code, 200)
        train.assert_not_called()
        self.assertNotIn("matplotlib.pyplot", sys.modules)
        self.assertIn("Dolo 650", response.context["ai_restock"])

    def test_suggestions_are_cached_and_invalidated_by_stock_changes(self):
        call_command("train_demand_model", stdout=open(os.devnull, "w"))
        self.log_search(self.pharmacy)

        first = generate_ai_restock()
        needed = first["pharmacy_allocation"][self.pharmacy.id]["Dolo 650"]

        with mock.patch("ml_service.ai_restock_service._compute_ai_restock") as compute:
            self.assertEqual(generate_ai_restock(), first)
            compute.assert_not_called()

        # Stocking the full amount clears the cache and the suggestion.
        Inventory.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=needed)
        self.assertEqual(generate_ai_restock()["pharmacy_allocation"], {})
