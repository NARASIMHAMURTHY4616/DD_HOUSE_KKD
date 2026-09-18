# DD House Kakinada — Backend & Database

Backend API and database service for **DD House Kakinada**, an artisanal cake and food store in Kakinada, Andhra Pradesh.

Built with **Python 3.13**, **FastAPI**, and **MongoDB**. Designed for pickup orders, verified product catalogs, strict server-side pricing, secure 4-digit pickup PIN verification, automated cancellation windows, and clean integration points for the React frontend and RAG knowledge assistant.

---

## Verified Business Information

- **Business**: DD House
- **Type**: Cake & food store
- **Location**: Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003
- **Hours**: 4:00 PM – 11:00 PM (Every day)
- **Phone**: 7013522727
- **Fulfillment**: Store Pickup ONLY (No delivery service)
- **Parking Advice**: DMart parking may be used by customers as friendly advice (not official DD House parking)
- **Pre-booking**: Customers can pre-book 4 hours in advance or place same-day orders
- **Preparation Time**: 15 minutes (normal) to 20 minutes (heavy rush)

---

## Architecture & Tech Stack

- **Framework**: FastAPI (asynchronous REST API)
- **Database**: MongoDB (via PyMongo)
- **Data Validation**: Pydantic v2
- **Testing**: Pytest with `mongomock` (no live MongoDB required for unit tests)
- **Architecture**: Modular, single-service MVP with distinct layers:
  - `routes/`: HTTP API controllers and status codes
  - `services/`: Core business logic, pricing calculations, cancellation policy
  - `database/repositories/`: PyMongo collection abstraction
  - `models/` & `schemas/`: Pydantic domain models and API contracts
  - `utils/`: Atomic Order ID generator, secure PIN generator, validation logic

---

## Directory Structure

```
DD_HOUSE_KKD/
├── requirements.txt           # Python dependencies
├── .env.example               # Template environment variables
├── pytest.ini                 # Pytest configuration
├── README.md                  # System documentation
├── database/
│   ├── schemas/
│   │   ├── products.json      # Product JSON schema
│   │   └── orders.json        # Order JSON schema
│   └── seed/
│       ├── products.json      # Verified 12 products seed data
│       └── seed_database.py   # Idempotent DB seeding script
├── backend/
│   └── app/
│       ├── main.py            # FastAPI entry point, CORS, and error handlers
│       ├── config/
│       │   └── settings.py    # Environment settings via Pydantic
│       ├── database/
│       │   ├── connection.py  # Mongo client management & indexes
│       │   └── repositories/
│       │       ├── product_repository.py
│       │       └── order_repository.py
│       ├── models/            # Domain models (Product, Order)
│       ├── schemas/           # Pydantic request/response schemas
│       ├── services/          # Business logic services (Pricing, Orders, Chat)
│       ├── routes/            # API endpoints (Products, Orders, Chat)
│       ├── utils/             # Validators, Order ID & PIN generators
│       └── tests/             # Unit tests (test_products, test_orders, test_chat)
└── tests/
    └── integration/
        └── test_api.py        # End-to-end integration tests
```

---

## Environment Variables

Copy `.env.example` to `.env` to configure the environment:

```bash
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port for the FastAPI server |
| `ENVIRONMENT` | `development` | Runtime environment (`development` / `production`) |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `DATABASE_NAME` | `dd_house_kakinada` | Database name |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed frontend origins (comma-separated) |
| `RAG_SERVICE_URL` | `http://localhost:8001` | Upstream RAG pipeline URL |
| `STORE_PHONE` | `7013522727` | Verified store contact phone |
| `CASH_PAYMENT_DEFAULT_STATUS` | `PENDING` | Default status for Cash orders (TBD advance settlement) |

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13.7)
- MongoDB instance (local or MongoDB Atlas)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Seed Database
Seed the 12 verified products into MongoDB:
```bash
python database/seed/seed_database.py
```

### 4. Start Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation (Swagger UI): `http://localhost:8000/docs`

---

## Database Collections & Verified Products

### `products` Collection
Stores the 12 verified DD House products:

| ID | Name | Category | Price | Customizable |
| :--- | :--- | :--- | :--- | :--- |
| `CB001` | Chocolate Cake Bowl | Cake Bowl | ₹89 | Yes |
| `CB002` | Double Chocolate | Cake Bowl | ₹89 | Yes |
| `CB003` | Triple Chocolate | Cake Bowl | ₹99 | Yes |
| `CB004` | Choco Truffle | Cake Bowl | ₹99 | Yes |
| `CB005` | Nutella | Cake Bowl | ₹89 | Yes |
| `CB006` | Oreo | Cake Bowl | ₹89 | Yes |
| `CB007` | Vanilla | Cake Bowl | ₹89 | Yes |
| `CB008` | Butterscotch | Cake Bowl | ₹89 | Yes |
| `BR001` | Chocolate Brownie | Brownie | ₹50 | No |
| `BR002` | Choco-Chip Brownie | Brownie | ₹50 | No |
| `CL001` | Chocolate Lollipop | Cake Lollipop | ₹30 | No |
| `CL002` | Vanilla Lollipop | Cake Lollipop | ₹30 | No |

### `orders` Collection
Tracks orders with the following schema:
- `order_id`: Unique format `DDYYYYMMDDXXXX` (e.g. `DD202609180001`)
- `pickup_pin`: 4-digit numeric code (e.g. `4821`)
- `customer`: Name and 10-digit mobile number
- `items`: Verified products, verified unit price, server-calculated subtotal, and optional customization
- `total_amount`: Server-calculated total in INR
- `pickup_time`: Customer scheduled pickup time
- `payment`: Method (`UPI` or `CASH`) and status (`PENDING`, `PAID`, `REFUNDED`)
- `status`: `PENDING_PAYMENT`, `CONFIRMED`, `PREPARING`, `READY_FOR_PICKUP`, `PICKED_UP`, `CANCELLED`
- `cancellation`: `cancelled` (bool), `cancelled_at` (ISO), `refund_status`, `refund_amount`

---

## Core Security & Business Rules

1. **Server-Side Price Calculation**:
   - The backend queries verified prices from MongoDB for every `product_id`.
   - Any `price` or `subtotal` sent by the client is strictly ignored. The frontend can never dictate the order total.
2. **Customization Rules**:
   - Only **Cake Bowls** support customization.
   - Allowed flavours: Vanilla, Chocolate, Red Velvet, Butterscotch, Oreo, Nutella, Fruit flavours, Other flavours available in the menu.
   - Allowed fillings: Chocolate cream, Nutella, Oreo cream, Caramel, Fruit filling.
   - Allowed toppings: Chocolate chips, Oreo pieces, Sprinkles, Nuts, Brownie pieces, Cherries.
   - Allowed sauces: Chocolate, White chocolate, Caramel, Nutella.
   - Name/message is written on the **BOX**, not on the cake itself.
   - Brownies and Cake Lollipops explicitly reject customization attempts.
   - Customization prices are UNKNOWN/TBD and not fabricated.
3. **Strict Pickup Verification**:
   - Orders must be in **`READY_FOR_PICKUP`** status for pickup verification.
   - Customers provide their 4-digit pickup PIN to complete pickup (`POST /api/orders/{order_id}/pickup`).
   - The PIN is excluded from public lookup endpoints (`GET /api/orders/{order_id}`).
4. **Cancellation Rules**:
   - Within **5 minutes** of order creation: eligible for full refund (`FULL_REFUND`), refund amount equals total order amount.
   - After **5 minutes**: cancellation recorded as `MANUAL_REVIEW_REQUIRED`, refund amount set to `null` (no fabricated fee or percentage).
5. **Customer Queue & Token System**:
   - Every order receives a daily sequential token (e.g. `Q001`, `Q002`, `Q003`) atomically generated via MongoDB `$inc` counters.
   - Queue counters reset daily at midnight in **Indian Standard Time (IST / Asia/Kolkata)**.
   - **Queue Position**: Calculated dynamically based on active orders (`PENDING_PAYMENT`, `CONFIRMED`, `PREPARING`, `READY_FOR_PICKUP`) placed earlier on the same day. Completed (`PICKED_UP`) and `CANCELLED` orders drop out of the active queue (position `0`) while retaining their historical queue token.
   - **Estimated Ready Time (ETA)**: Deterministically calculated as an operational estimate (15 to 20 minutes from placement in IST, reflecting standard store preparation time). It is an estimate and not a delivery guarantee.
   - **PIN & Privacy Isolation**: Pickup PIN is strictly hidden from queue tracking endpoints. Customer phone numbers are masked (`******3210`).
   - **Payment Integrity**: Having a queue token does not bypass payment confirmation; `PENDING_PAYMENT` orders remain unpaid until confirmed.
6. **RAG Integration Point**:
   - `POST /api/chat` forwards inquiries to the RAG service.
   - Customer and transactional data are never exposed to RAG.
   - If the RAG service is unreachable, returns `503 Service Unavailable` with error code `RAG_SERVICE_UNAVAILABLE` and zero hallucinated answers.

---

## API Endpoints & Examples

### 1. Health Check
`GET /api/health`

**Response (`200 OK`)**:
```json
{
  "success": true,
  "status": "healthy",
  "service": "DD House Kakinada Backend",
  "store": {
    "name": "DD House",
    "location": "Venkat Nagar, Jayendra Nagar, Siddartha Nagar, Kakinada, Andhra Pradesh – 533003",
    "phone": "7013522727",
    "hours": "16:00 - 23:00"
  }
}
```

### 2. Get Products
`GET /api/products` (Optional filter: `?category=Cake%20Bowl`)

**Response (`200 OK`)**:
```json
{
  "success": true,
  "count": 12,
  "data": [
    {
      "product_id": "CB003",
      "name": "Triple Chocolate",
      "category": "Cake Bowl",
      "price": 99.0,
      "available": true,
      "customizable": true
    }
  ]
}
```

### 3. Create Order
`POST /api/orders`

**Request Body**:
```json
{
  "customer": {
    "name": "Ravi Kumar",
    "phone": "9876543210"
  },
  "items": [
    {
      "product_id": "CB003",
      "quantity": 2,
      "customization": {
        "flavor": "Chocolate",
        "filling": "Nutella",
        "toppings": ["Brownie pieces"],
        "sauce": "Caramel",
        "message": "Happy Birthday!"
      }
    },
    {
      "product_id": "BR001",
      "quantity": 1
    }
  ],
  "pickup_time": "18:30",
  "payment": {
    "method": "UPI"
  }
}
```

**Response (`201 Created`)**:
```json
{
  "success": true,
  "data": {
    "order_id": "DD202609180001",
    "pickup_pin": "4821",
    "queue": {
      "token": "Q001",
      "position": 1,
      "queue_date": "2026-09-18",
      "seq": 1,
      "estimated_ready_at": "2026-09-18T18:45:00+05:30"
    },
    "customer": {
      "name": "Ravi Kumar",
      "phone": "******3210"
    },
    "items": [
      {
        "product_id": "CB003",
        "name": "Triple Chocolate",
        "quantity": 2,
        "unit_price": 99.0,
        "subtotal": 198.0,
        "customization": {
          "flavor": "Chocolate",
          "filling": "Nutella",
          "toppings": ["Brownie pieces"],
          "sauce": "Caramel",
          "message": "Happy Birthday!",
          "note": "Message is written on the BOX, not on the cake."
        }
      },
      {
        "product_id": "BR001",
        "name": "Chocolate Brownie",
        "quantity": 1,
        "unit_price": 50.0,
        "subtotal": 50.0,
        "customization": null
      }
    ],
    "total_amount": 248.0,
    "pickup_time": "18:30",
    "payment": {
      "method": "UPI",
      "status": "PAID"
    },
    "status": "CONFIRMED",
    "cancellation": {
      "cancelled": false,
      "cancelled_at": null,
      "refund_status": null,
      "refund_amount": null
    },
    "created_at": "2026-09-18T10:30:00.000000+00:00",
    "updated_at": "2026-09-18T10:30:00.000000+00:00"
  }
}
```

### 4. Public Order Lookup (PIN Masked)
`GET /api/orders/DD202609180001`

**Response (`200 OK`)**:
Returns full order data (including `queue` details), omitting `pickup_pin` for customer privacy and security. Customer phone is masked.

### 5. Order Tracking Status
`GET /api/orders/DD202609180001/status`

**Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "order_id": "DD202609180001",
    "status": "CONFIRMED",
    "pickup_time": "18:30",
    "queue": {
      "token": "Q001",
      "position": 1,
      "queue_date": "2026-09-18",
      "seq": 1,
      "estimated_ready_at": "2026-09-18T18:45:00+05:30"
    },
    "payment": {
      "method": "UPI",
      "status": "PAID"
    },
    "cancellation": {
      "cancelled": false,
      "cancelled_at": null,
      "refund_status": null,
      "refund_amount": null
    }
  }
}
```

### 6. Customer Queue Token Lookup
`GET /api/orders/DD202609180001/queue`

Dedicated lightweight endpoint for customers tracking their queue progress from their car/on the road without exposing full order details or PIN.

**Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "order_id": "DD202609180001",
    "queue": {
      "token": "Q001",
      "position": 1,
      "queue_date": "2026-09-18",
      "seq": 1,
      "estimated_ready_at": "2026-09-18T18:45:00+05:30"
    },
    "status": "CONFIRMED"
  }
}
```

### 7. Pickup Verification
`POST /api/orders/DD202609180001/pickup`

**Request Body**:
```json
{
  "pickup_pin": "4821"
}
```

**Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "order_id": "DD202609180001",
    "status": "PICKED_UP",
    "message": "Order successfully verified and marked as PICKED_UP."
  }
}
```

### 8. Cancel Order
`POST /api/orders/DD202609180001/cancel`

**Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "order_id": "DD202609180001",
    "status": "CANCELLED",
    "message": "Order cancelled within 5-minute window. Eligible for full refund.",
    "cancellation": {
      "cancelled": true,
      "cancelled_at": "2026-09-18T10:32:00.000000+00:00",
      "refund_status": "FULL_REFUND",
      "refund_amount": 248.0
    }
  }
}
```

### 9. Assistant / RAG Chat
`POST /api/chat`

**Request Body**:
```json
{
  "message": "What flavours are available for cake bowls?"
}
```

**Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "response": "Available flavours for cake bowls include Vanilla, Chocolate, Red Velvet, Butterscotch, Oreo, Nutella, and Fruit flavours.",
    "source": "rag"
  }
}
```

---

## Running Automated Tests

Run the complete test suite:
```bash
python -m pytest -v
```

All 70 test cases run using `mongomock` and do not require an active external database connection.
