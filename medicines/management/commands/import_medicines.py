import csv
from django.core.management.base import BaseCommand
from medicines.models import Medicine

class Command(BaseCommand):
    help = "Import medicines from CSV file"

    def handle(self, *args, **kwargs):
        file_path = "medicines/medicines_dataset.csv"

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0

            for row in reader:
                obj, created = Medicine.objects.get_or_create(
                    brand_name=row['brand_name'],
                    generic_name=row['generic_name'],
                    composition=row['composition'],
                    strength=row['strength'],
                    dosage_form=row['dosage_form'],
                    category=row['category'],
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} medicines imported successfully."))
