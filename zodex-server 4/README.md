# Zodex Server

FastAPI backend for the `zodex-client` landing page using MongoDB via MongoEngine. It ships with:

- Public REST APIs for hero/content/services/products/process/portfolio/testimonials/contact
- Contact inquiry and newsletter submission endpoints
- Template-based admin panel for managing homepage content
- MongoEngine models with seed data matching the current frontend
- JWT-based admin API login for future frontend/admin integrations

## Run locally

```bash
cd /Users/abhay/Downloads/edumanage_pro/zodex-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MONGODB_URI=mongodb://127.0.0.1:27017
export MONGODB_DB=zodex_server
python3 run.py
```

Open:

- API docs: `http://127.0.0.1:8008/docs`
- Admin panel: `http://127.0.0.1:8008/admin/login`

Default admin credentials:

- Username: `admin`
- Password: `admin123`

## Important endpoints

- `GET /api/v1/home`
- `GET /api/v1/services`
- `GET /api/v1/products`
- `GET /api/v1/process-steps`
- `GET /api/v1/portfolio-cases`
- `GET /api/v1/testimonials`
- `GET /api/v1/reasons`
- `GET /api/v1/stats`
- `GET /api/v1/contact-info`
- `POST /api/v1/contact-inquiries`
- `POST /api/v1/newsletter-subscriptions`
- `POST /api/v1/admin/login`

## Frontend integration note

The current `zodex-client` is static. To wire it up, replace hardcoded arrays with `GET /api/v1/home` and post the contact form to `POST /api/v1/contact-inquiries`.

## Local mock mode

If MongoDB is not running locally, you can still boot the app in mock mode:

```bash
export USE_MOCK_DB=true
python3 run.py
```
