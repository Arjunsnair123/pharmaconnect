from django.db import models
from pharmacies.models import Pharmacy
from medicines.models import Medicine

class Inventory(models.Model):
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pharmacy.name} - {self.medicine.brand_name} ({self.quantity})"
