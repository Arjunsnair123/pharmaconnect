# PharmaConnect

[![Tests](https://github.com/Arjunsnair123/pharmaconnect/actions/workflows/tests.yml/badge.svg)](https://github.com/Arjunsnair123/pharmaconnect/actions/workflows/tests.yml)

A pharmacy locator. Patients search for a medicine and see which nearby
pharmacies have it in stock; pharmacies manage their inventory and get
restock suggestions based on local search demand.

Built with Django 6 and Django REST Framework.

## Features

- **Medicine availability search** – pharmacies near you that stock a medicine, nearest first.
- **Emergency mode** – restrict any search to 24x7 pharmacies.
- **Generic substitutes** – alternatives with the same generic and dosage form, and where they are in stock nearby.
- **Pharmacy inventory management** – each pharmacy account manages only its own stock.
- **Restock suggestions** – a demand forecast is split across pharmacies according to what people searched for near them, then compared with current stock.
- **Roles** – patient, pharmacy and admin. Anyone can register as a patient; pharmacy accounts are linked by an admin.
- **API docs** – OpenAPI schema and Swagger UI.

## Architecture

| App | Responsibility |
|---|---|
| `accounts` | Login, registration, `Profile` (role) |
| `pharmacies` | `Pharmacy` model, nearest-pharmacy API, pharmacy dashboard, distance helpers |
| `medicines` | `Medicine` model, search, autocomplete and substitute APIs, CSV import command |
| `inventory` | `Inventory` model, availability API, stock management page |
| `ml_service` | `SearchLog`, demand allocation, restock suggestions, forecast API, training command |
| `ml` | Demand forecast model (training and prediction), training data |
| `dashboard` | Patient dashboard and live map pages |
| `pharmaconnect` | Settings, URLs, shared query validation and pagination (`api.py`) |
| `theme` | Tailwind theme app |

Design points:

- **Location search** – a latitude/longitude bounding box is applied in the
  database (indexed) to discard distant pharmacies; the haversine formula then
  gives exact distances for the remaining candidates. Searches are limited to a
  radius (default 50 km, `?radius_km=` to change).
- **Restock pipeline** – every availability search is logged against the
  nearest pharmacy. A linear-regression model forecasts total area demand for
  the next week; that total is split by medicine and pharmacy in proportion to
  the logged searches, and current stock is subtracted.
- **Training is offline** – `manage.py train_demand_model` trains and saves
  the model; web requests only load it and predict. Suggestions are cached and
  invalidated whenever stock changes or the model is retrained.
- **Authentication** – session auth for the web pages, JWT for API clients.
  Both are accepted on every API endpoint.
- **Data integrity** – one pharmacy per user, one inventory row per
  pharmacy and medicine, and non-negative quantities, all enforced by database
  constraints.

## Setup

Requires Python 3.13.

```bash
git clone https://github.com/Arjunsnair123/pharmaconnect.git
cd pharmaconnect

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then set DJANGO_SECRET_KEY and DJANGO_DEBUG=True

python manage.py migrate
python manage.py import_medicines       # load the medicine catalogue
python manage.py train_demand_model     # train the demand forecast model
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000/. Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### Creating a pharmacy account

Self-registration always creates a patient. To set up a pharmacy, sign in to
`/admin/` as a superuser and:

1. Create the user (or have them register).
2. Set their `Profile` role to `PHARMACY`.
3. Create a `Pharmacy` and select that user as its owner.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(required)* | Django secret key |
| `DJANGO_DEBUG` | `False` | Debug mode; `True` for local development only |
| `DJANGO_ALLOWED_HOSTS` | *(empty)* | Comma-separated hostnames; required when debug is off |
| `DATABASE_URL` | SQLite `db.sqlite3` | Database, e.g. `postgres://user:pass@host:5432/db` |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | Allow any origin (development only) |
| `CORS_ALLOWED_ORIGINS` | *(empty)* | Comma-separated allowed origins |
| `DEFAULT_SEARCH_RADIUS_KM` | `50` | Search radius when `radius_km` is not sent |
| `MAX_SEARCH_RADIUS_KM` | `500` | Largest `radius_km` a client may request |
| `RESTOCK_CACHE_TIMEOUT` | `900` | Seconds to cache restock suggestions |
| `DEMAND_MODEL_PATH` | `ml/demand_model.joblib` | Where the trained model is saved and loaded |

## Running tests

```bash
python manage.py test
```

The suite runs on SQLite by default. GitHub Actions runs it on every push
against both SQLite and PostgreSQL (`.github/workflows/tests.yml`).

## API

Interactive docs: `/api/docs/` (Swagger UI). Schema: `/api/schema/`.

List responses are paginated: `?page=` and `?page_size=` (default 20, max 100).
Invalid or missing parameters return `400` with per-field errors.

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| POST | `/api/token/` | – | `username`, `password` (body) | Obtain a JWT access and refresh token |
| POST | `/api/token/refresh/` | – | `refresh` (body) | Refresh an access token |
| GET | `/api/medicines/search/` | – | `q` | Search medicines by brand or generic name |
| GET | `/api/medicines/suggest/` | – | `q` (min 2 chars) | Up to 8 brand names for autocomplete |
| GET | `/api/medicines/substitutes/` | – | `brand` | Medicines with the same generic and dosage form |
| GET | `/api/medicines/smart-substitutes/` | – | `brand`, `lat`, `lon`, `radius_km`, `emergency` | Substitutes in stock nearby, nearest first |
| GET | `/api/pharmacies/nearest/` | – | `lat`, `lon`, `radius_km` | Pharmacies within the radius, nearest first |
| GET | `/api/inventory/availability/` | User | `medicine`, `lat`, `lon`, `radius_km`, `emergency` | Pharmacies stocking a medicine, nearest first |
| GET | `/api/ml/forecast/` | Staff | – | Next week's demand forecast and per-pharmacy allocation |

"User" means a session cookie or `Authorization: Bearer <access token>`.

### Web pages

| Path | Who | Page |
|---|---|---|
| `/accounts/register/`, `/accounts/login/`, `/accounts/logout/` | Anyone | Account pages |
| `/dashboard/patient/` | Signed in | Patient dashboard |
| `/dashboard/map/` | Signed in | Live map and emergency finder |
| `/api/pharmacies/dashboard/` | Pharmacy | Pharmacy dashboard with restock suggestions |
| `/api/inventory/pharmacy/inventory/` | Pharmacy | Stock management |
| `/admin/` | Staff | Django admin |
