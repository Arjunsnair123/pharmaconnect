from django.db import models
from django.contrib.auth.models import User

class Pharmacy(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_24x7 = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # Serves the bounding-box prefilter in location searches.
            models.Index(fields=["latitude", "longitude"], name="pharmacy_lat_lon_idx"),
        ]

    def __str__(self):
        return self.name
