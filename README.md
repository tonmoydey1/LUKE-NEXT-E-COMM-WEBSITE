# LuxeNest

LuxeNest is a production-oriented Django ecommerce platform with premium UI, secure account flows, product catalog, cart and checkout, Razorpay-ready payments, PDF invoices, automated emails, India pincode delivery checks, order tracking, and an admin analytics dashboard.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Database

SQLite is used by default for local development. For PostgreSQL or MySQL, edit `.env`:

```env
DB_ENGINE=postgresql
DB_NAME=luxenest
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5432
```

Use `DB_ENGINE=mysql` with MySQL credentials for MySQL.

## Modules

- `apps.accounts`: registration, login, OTP verification, profile, addresses, premium membership.
- `apps.catalog`: categories, products, variants, gallery, reviews, wishlist, filtering, autocomplete search.
- `apps.orders`: cart, coupons, checkout, pincode serviceability, order lifecycle, tracking, invoices.
- `apps.payments`: Razorpay test-mode architecture, transaction records, success/failure handling.
- `apps.dashboard`: staff dashboard with revenue, orders, customers, low stock, and payment summaries.

## Razorpay

Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`. Without keys, LuxeNest uses a safe demo fallback so portfolio demos still work.

For real-time UPI/Card payments, create Razorpay API keys from the Razorpay Dashboard and replace the placeholder values:

```env
RAZORPAY_KEY_ID=rzp_test_your_actual_key
RAZORPAY_KEY_SECRET=your_actual_secret
```

Restart the server after changing `.env`. Premium and checkout payments use Razorpay Standard Checkout and verify the payment signature before activating the membership or confirming the order.

## Email

Development uses Django's console email backend. Production settings read SMTP values from `.env` and send HTML emails for OTPs, welcome messages, order updates, payment confirmations, invoices, and premium activation.

## Logo Concept

The LuxeNest logo is available at `static/img/logo.svg`: a professional blue commerce tile with a gold luxury accent and interlocked LN monogram, paired with clean serif/sans typography.
