# Moonlight Flame – Candle E-commerce Website

Django-based candle store with authentication, persistent cart, checkout, order history and inventory management.

## Features
- User registration and login
- Persistent cart for authenticated customers
- Add, remove and update cart quantities
- Stock validation and inventory deduction at checkout
- Delivery address capture
- Shipping calculation (free over ₹499, otherwise ₹49)
- COD handling fee of ₹30
- Order history with status and payment information
- Django admin for candles and orders
- CSRF-protected POST actions

## Setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Create an admin user:

```bash
python manage.py createsuperuser
```

## Environment

Copy `.env.example` values into your deployment environment. Do not commit real secrets.

## Production checklist
- Set `DJANGO_DEBUG=False`
- Set a strong `DJANGO_SECRET_KEY`
- Set `DJANGO_ALLOWED_HOSTS` to the real domain
- Serve static/media files through the production web server/storage
- Configure HTTPS
- Configure a real payment gateway before advertising online/card/UPI payments
