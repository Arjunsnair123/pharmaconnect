from django.db import models
from django.contrib.auth.models import User
from pharmacies.models import Pharmacy

class SearchLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="searches")
    medicine = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Allow null temporarily so migrations work and old rows don't break
    nearest_pharmacy = models.ForeignKey(
        Pharmacy,
        on_delete=models.CASCADE,
        related_name="search_hits",
        null=True,
        blank=True
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.nearest_pharmacy:
            return f"{self.user.username} searched {self.medicine} near {self.nearest_pharmacy.name}"
        return f"{self.user.username} searched {self.medicine}"
