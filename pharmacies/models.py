from django.db import models
from django.contrib.auth.models import User

class Pharmacy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_24x7 = models.BooleanField(default=False)

    def __str__(self):
        return self.name
