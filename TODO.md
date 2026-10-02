# PharmacoConnect: Populate New Medicines CSV Task

## Plan Summary

- User has updated `medicines/medicines_dataset.csv`.
- Use existing Django management command `python manage.py import_medicines` to populate DB safely (get_or_create).
- Verify count and API.
- No model changes needed.

## Steps

- [x] Step 1: Run import command (64 new medicines imported)
- [x] Step 2: Verify data loaded (Medicine.objects.count() == 76)
- [x] Step 3: Test API endpoint (server running; test http://localhost:8000/api/medicines/search/?q=Dolo)
- [x] Complete
