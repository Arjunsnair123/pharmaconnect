# PharmaConnect

Django 6 + DRF pharmacy locator: medicine availability search, generic
substitutes, emergency 24x7 mode, pharmacy inventory, restock suggestions.
See README.md for features, env vars and the endpoint table.

## Commands

The virtualenv lives outside the repo at `../myenv` (there is no `python` on PATH).

```bash
../myenv/bin/python manage.py test                 # full suite
../myenv/bin/python manage.py test inventory       # one app
../myenv/bin/python manage.py makemigrations --check --dry-run
../myenv/bin/python manage.py train_demand_model   # needed once; model file is gitignored
../myenv/bin/python manage.py spectacular --validate --file /dev/null   # API schema check
../myenv/bin/python manage.py runserver
```

Settings read `.env` (gitignored). `DJANGO_SECRET_KEY` is required; the app
will not start without it.

## Layout

- `accounts` – login/registration, `Profile.role`; `get_role(user)` is the safe way to read a role
- `pharmacies` – `Pharmacy`, nearest API, dashboard, `utils.py` (haversine, bounding box)
- `medicines` – `Medicine`, search/suggest/substitute APIs
- `inventory` – `Inventory`, availability API, stock page
- `ml_service` – `SearchLog`, allocator, restock service (cached), forecast API, training command
- `ml` – forecast model code and training CSV (plain package, not a Django app)
- `pharmaconnect/api.py` – shared query-param serializers and pagination

## Conventions

- **Roles are never taken from client input.** Registration always creates a
  PATIENT; pharmacy accounts are linked by an admin in `/admin/`.
- **A pharmacy is resolved from `request.user.pharmacy`** (one-to-one), never
  from an id in the request. Views must not create pharmacies implicitly.
- **Query params are validated with serializers** from `pharmaconnect/api.py`
  (`is_valid(raise_exception=True)`). Bad input is a 400, never a 500. Add an
  `@extend_schema` so the endpoint appears correctly in the docs.
- **Location queries** apply `bounding_box_filter` in the database, then
  haversine in Python, then drop rows beyond `radius_km`.
- **List endpoints are paginated** with `paginate()`. Endpoints the map UI
  consumes keep their existing keys (`results`, `nearest_substitutes`,
  `substitutes`) and add `count`/`next`/`previous` alongside.
- **Look up medicines by brand with `filter(...).first()`**; `brand_name` is not unique.
- **Restock data is keyed by pharmacy id**, not name.
- **No training, CSV reading or matplotlib in request code.** Requests call
  `predict_next_week_demand()`, which only loads the saved model.
- **Anything that changes what restock suggestions depend on must call
  `invalidate_restock_cache()`** (inventory changes already do, via signals).
- **Auth** is the global default (JWT + session); don't set
  `authentication_classes` per view.
- Model changes need a migration; CI fails on missing ones.

## Testing

- Django `TestCase` + DRF `APIClient`; tests live in each app's `tests.py`.
- Build fixtures in the test; never rely on `db.sqlite3` contents.
- Tests that touch the forecast model inherit `RestockTestCase`
  (`ml_service/tests.py`), which isolates the model path and clears the cache.
- CI (`.github/workflows/tests.yml`) runs the suite on SQLite and PostgreSQL.
  Local development is SQLite only, so avoid SQLite-specific behaviour.

## Working style for this repo

- Keep changes minimal and focused; don't refactor unrelated code or change
  UI behaviour unless fixing a bug.
- Commit messages explain the non-obvious "why" of each change.
- Work on a branch, not `main`. Don't push; the owner pushes.
