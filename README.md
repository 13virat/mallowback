# 🎂 Cakemallow Backend — Full Platform

Production-grade Django REST API for the **Cakemallow** bakery platform.

## Apps Overview

| App | Purpose |
|-----|---------|
| `accounts` | Custom user model, JWT auth, profiles |
| `products` | Categories, products, variants, filtering |
| `cart` | Per-user cart with quantity management |
| `orders` | Order lifecycle, addresses, cancellation |
| `customization` | Custom cake requests |
| `reviews` | Product reviews (1–5 ★, one per user) |
| `payments` | Razorpay integration + Cash on Delivery |
| `coupons` | Discount codes (%, flat, free delivery) |
| `loyalty` | Points system with Bronze/Silver/Gold/Platinum tiers |
| `delivery_slots` | Time slot booking with capacity limits |
| `store_locations` | Multiple stores + pincode serviceability |
| `notifications` | Email / SMS / WhatsApp via templates |
| `wishlist` | Save products for later |
| `analytics` | Admin dashboard KPIs and charts |

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Full API Reference

### Auth  `/api/auth/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register/` | — | Register |
| POST | `/login/` | — | Get JWT tokens |
| POST | `/token/refresh/` | — | Refresh token |
| POST | `/logout/` | 🔒 | Blacklist token |
| GET/PATCH | `/profile/` | 🔒 | View/update profile |

### Products  `/api/products/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | — | List products (`?category`, `?search`, `?eggless`, `?featured`) |
| GET | `/<id>/` | — | Product detail |
| GET | `/categories/` | — | List categories |

### Cart  `/api/cart/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | View cart |
| POST | `/add/` | 🔒 | Add item |
| PATCH/DELETE | `/items/<id>/` | 🔒 | Update qty / remove |
| DELETE | `/clear/` | 🔒 | Clear cart |

### Orders  `/api/orders/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | My orders |
| POST | `/create/` | 🔒 | Place order (supports coupon_code) |
| GET | `/<id>/` | 🔒 | Order detail |
| POST | `/<id>/cancel/` | 🔒 | Cancel order |
| GET/POST | `/addresses/` | 🔒 | Addresses |

### Payments  `/api/payments/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/initiate/<order_id>/` | 🔒 | Create Razorpay order |
| POST | `/verify/` | 🔒 | Verify & confirm payment |
| POST | `/cod/<order_id>/` | 🔒 | Cash on delivery |

### Coupons  `/api/coupons/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | List available coupons |
| POST | `/apply/` | 🔒 | Validate & preview discount |

### Loyalty  `/api/loyalty/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | Points balance + history |
| POST | `/redeem/` | 🔒 | Redeem points for discount |

### Delivery Slots  `/api/delivery-slots/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/?date=YYYY-MM-DD` | — | Available slots on date |
| POST | `/book/` | 🔒 | Book a slot for an order |

### Store Locations  `/api/stores/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | — | All stores (`?city=Lucknow`) |
| GET | `/check-pincode/?pincode=226001` | — | Delivery availability + charges |

### Notifications  `/api/notifications/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | My notifications |

### Wishlist  `/api/wishlist/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | 🔒 | My wishlist |
| POST | `/toggle/<product_id>/` | 🔒 | Add/remove product |

### Reviews  `/api/reviews/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/` | 🔒 | Add review |
| GET | `/product/<id>/` | — | Product reviews |
| DELETE | `/<id>/delete/` | 🔒 | Delete own review |

### Custom Cake  `/api/custom-cake/`
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/` | — | Submit request |
| GET | `/my-requests/` | 🔒 | My requests |

### Analytics  `/api/analytics/`  🔒 Admin only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/summary/` | KPIs — orders, revenue, users |
| GET | `/revenue/daily/` | Daily revenue last 30 days |
| GET | `/revenue/monthly/` | Monthly revenue last 12 months |
| GET | `/top-products/` | Best-selling products |
| GET | `/orders/status/` | Orders per status |
| GET | `/orders/recent/` | Last 20 orders |

## Loyalty Tiers

| Tier | Points Required | Earning Rate |
|------|----------------|--------------|
| 🥉 Bronze | 0 | 1 pt per ₹10 |
| 🥈 Silver | 500 lifetime pts | 1 pt per ₹10 |
| 🥇 Gold | 1,500 lifetime pts | 1 pt per ₹10 |
| 💎 Platinum | 5,000 lifetime pts | 1 pt per ₹10 |

2 points = ₹1 discount at redemption.

## Payment Flow (Razorpay)

```
1. POST /api/orders/create/        → get order_id
2. POST /api/payments/initiate/<order_id>/  → get razorpay_order_id + key
3. Open Razorpay checkout on frontend
4. POST /api/payments/verify/      → confirm payment, award loyalty points
```
