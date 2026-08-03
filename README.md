# AI Fatah FastAPI E-commerce Store

A complete server-rendered grocery e-commerce project using FastAPI, Jinja2, SQLAlchemy and PostgreSQL. It includes a customer storefront, session cart, website checkout, WhatsApp ordering, local product-image uploads and a protected admin dashboard.

## Main features

### Customer storefront

- Responsive grocery homepage inspired by a modern Pakistani supermarket
- Product search and category filtering
- Product detail pages
- Live price, compare-at price, stock quantity and availability
- Session-based shopping cart
- Website checkout with cash-on-delivery or bank-transfer selection
- WhatsApp cart order with a pre-filled product summary
- Floating WhatsApp support button

### Admin dashboard

- Secure email/password login with Argon2 password hashing
- CSRF protection for form submissions
- Dashboard statistics and low-stock warnings
- Create and edit products
- Set product name, slug, description, unit and category
- Change price and optional compare-at price
- Change stock quantity
- Set `In stock`, `Out of stock` or `Sold out`
- Upload JPG, PNG or WEBP product images locally
- Feature, hide or archive products
- Create and hide categories
- View website orders and customer details
- Change order status from pending through delivered/cancelled

## Project structure

```text
ai_fatah_fastapi/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   │   ├── admin.py
│   │   ├── category.py
│   │   ├── order.py
│   │   └── product.py
│   ├── routers/
│   │   ├── admin.py
│   │   ├── api.py
│   │   ├── cart.py
│   │   ├── checkout.py
│   │   └── store.py
│   ├── services/
│   │   ├── cart_service.py
│   │   ├── order_service.py
│   │   ├── slug.py
│   │   └── storage.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   ├── admin/
│   │   └── store/
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   ├── schemas.py
│   └── web.py
├── alembic/versions/0001_initial_schema.py
├── scripts/seed.py
├── tests/test_smoke.py
├── uploads/
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Windows setup (recommended for you)

### 1. Open the project in PowerShell

```powershell
cd "D:\Projects\AI Fatah Store\ai_fatah_fastapi"
```

### 2. Create and activate a virtual environment

```powershell
py -m venv venv
venv\Scripts\activate
```

### 3. Install packages

```powershell
pip install -r requirements.txt
```

### 4. Create the environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` and change at least:

```env
SECRET_KEY=put-a-long-random-secret-here
DATABASE_URL=postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/ai_fatah_store
WHATSAPP_NUMBER=923XXXXXXXXX
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=YourStrongPassword123!
```

The WhatsApp number must include the country code but not `+`, spaces or dashes.

### 5. Create the PostgreSQL database

In pgAdmin 4:

1. Expand your PostgreSQL server.
2. Right-click **Databases**.
3. Select **Create → Database**.
4. Set database name to `ai_fatah_store`.
5. Save it.

### 6. Run the database migration

```powershell
alembic upgrade head
```

After migrations work, set this in `.env`:

```env
AUTO_CREATE_TABLES=false
```

### 7. Create the admin and demo products

```powershell
python -m scripts.seed
```

The seed uses `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`.

### 8. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

Open:

- Storefront: `http://127.0.0.1:8000`
- Admin login: `http://127.0.0.1:8000/admin/login`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Quick setup without PostgreSQL

For a quick first test, set this in `.env`:

```env
DATABASE_URL=sqlite:///./ai_fatah.db
AUTO_CREATE_TABLES=true
```

Then run:

```powershell
python -m scripts.seed
uvicorn app.main:app --reload
```

Switch to PostgreSQL before production.

## How admin product changes reach customers

The storefront does not use hard-coded products. Every page reads the `products` and `categories` tables through SQLAlchemy.

```text
Admin form → FastAPI admin route → SQLAlchemy → PostgreSQL
                                              ↓
Customer request ← Jinja template ← FastAPI storefront route
```

Therefore, when the admin changes a price, stock quantity, status, name or image and saves it, the next customer page request shows the updated value automatically.

## Product images

For phase 1, uploaded images are validated and re-encoded with Pillow, saved inside `uploads/`, and the image path is stored in the database. The folder is mounted at `/uploads` by FastAPI.

Important deployment rule: use persistent disk storage for the `uploads/` folder. A later Cloudinary migration only requires replacing `save_product_image()` and `delete_local_image()` inside `app/services/storage.py`; product and admin code can remain almost unchanged.

## WhatsApp behavior

- The floating button opens a normal WhatsApp support conversation.
- **Order through WhatsApp** reads the current cart, creates a formatted message with product names, quantities and estimated total, then redirects the customer to `wa.me`.
- WhatsApp orders are completed inside WhatsApp and are not automatically stored as website orders.
- Website checkout creates a persistent database order that appears in the admin dashboard.

## Website order stock logic

When a website order is placed:

1. Products are locked during the database transaction where supported.
2. Current availability and quantity are checked again.
3. The order and order-item price snapshots are stored.
4. Product stock is reduced.
5. A product reaching zero automatically becomes `Out of stock`.

## Running tests

```powershell
pytest -q
```

The tests use a temporary SQLite database so they do not change your PostgreSQL data.

## Docker alternative

If Docker Desktop is installed:

```powershell
docker compose up --build -d
docker compose exec web python -m scripts.seed
```

Then open `http://127.0.0.1:8000`.

Before any public deployment, change the secret key, admin password, PostgreSQL password and WhatsApp number in `docker-compose.yml` or provide them through deployment environment variables.

## Current scope and next upgrades

Included now: catalog, admin dashboard, local uploads, cart, website orders, WhatsApp orders and order-status management.

Recommended later upgrades:

1. Cloudinary product-image storage
2. Customer accounts and saved addresses
3. Delivery-zone and delivery-fee rules
4. Online payment gateway
5. Email/SMS order notifications
6. Admin audit log and role permissions
