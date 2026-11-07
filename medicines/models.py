from django.db import models

class Medicine(models.Model):
    brand_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    composition = models.TextField()
    strength = models.CharField(max_length=50)
    dosage_form = models.CharField(max_length=50)  # tablet, syrup, injection
    category = models.CharField(max_length=100)    # antibiotic, analgesic, etc.

    def __str__(self):
        return f"{self.brand_name} ({self.generic_name})"
