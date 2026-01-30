from django.db import models
from django.contrib.auth.models import User
from pharmacies.models import Pharmacy

class Profile(models.Model):
    ROLE_CHOICES = (
        ('PATIENT', 'Patient'),
        ('PHARMACY', 'Pharmacy'),
        ('ADMIN', 'Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    pharmacy = models.ForeignKey(Pharmacy, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
