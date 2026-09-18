from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest
import mongomock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.connection import set_test_database


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["test_dd_house_orders"]
    set_test_database(mock_db)

    # Seed products
    seed_file = Path(__file__).resolve().parent.parent.parent.parent / "database" / "seed" / "products.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    mock_db.products.insert_many(products)

    yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


# Test 5: Create valid order
def test_create_valid_order(client):
    payload = {
        "customer": {"name": "Ravi Kumar", "phone": "9876543210"},
        "items": [
            {"product_id": "CB001", "quantity": 1}
        ],
        "pickup_time": "18:30",
        "payment": {"method": "UPI"}
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    order = data["data"]
    assert order["order_id"].startswith("DD")
    assert len(order["pickup_pin"]) == 4
    assert order["total_amount"] == 89.0
    assert order["status"] == "PENDING_PAYMENT"
    assert order["payment"]["status"] == "PENDING"
    assert order["payment"]["method"] == "UPI"
    assert order["customer"]["name"] == "Ravi Kumar"
    assert order["customer"]["phone"] == "9876543210"


# Test 6 & 7: Multiple products in one order & Correct server-side total
def test_multiple_products_order_and_total(client):
    # CB003 (Triple Chocolate) = 99 * 2 = 198
    # BR001 (Chocolate Brownie) = 50 * 1 = 50
    # CL001 (Chocolate Lollipop) = 30 * 2 = 60
    # Total = 308
    payload = {
        "customer": {"name": "Priya Sharma", "phone": "9123456780"},
        "items": [
            {"product_id": "CB003", "quantity": 2},
            {"product_id": "BR001", "quantity": 1},
            {"product_id": "CL001", "quantity": 2}
        ],
        "pickup_time": "19:00",
        "payment": {"method": "UPI"}
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    order = data["data"]
    assert len(order["items"]) == 3
    assert order["total_amount"] == 308.0


# Test 8: Frontend price manipulation attempt (tampered price ignored)
def test_frontend_price_manipulation_attempt(client):
    payload = {
        "customer": {"name": "Hacker", "phone": "9998887776"},
        "items": [
            {
                "product_id": "CB003",  # Official price 99
                "quantity": 2,
                "price": 1.0,           # Client attempts to pay 1 rupee
                "subtotal": 2.0
            }
        ],
        "pickup_time": "17:00"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    order = data["data"]
    # Total must be 99 * 2 = 198, ignoring the 1.0 submitted price
    assert order["items"][0]["unit_price"] == 99.0
    assert order["items"][0]["subtotal"] == 198.0
    assert order["total_amount"] == 198.0


# Test 9: Invalid quantity (<= 0)
def test_invalid_quantity(client):
    payload = {
        "customer": {"name": "Test User", "phone": "9876543210"},
        "items": [
            {"product_id": "CB001", "quantity": 0}
        ],
        "pickup_time": "18:00"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False


# Test 10: Empty order
def test_empty_order(client):
    payload = {
        "customer": {"name": "Test User", "phone": "9876543210"},
        "items": [],
        "pickup_time": "18:00"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False


# Test 11: Unknown product ID
def test_unknown_product(client):
    payload = {
        "customer": {"name": "Test User", "phone": "9876543210"},
        "items": [
            {"product_id": "UNKNOWN_CAKE", "quantity": 1}
        ],
        "pickup_time": "18:00"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "PRODUCT_NOT_FOUND"


# Test 12: Customization on cake bowl accepted
def test_customization_on_cake_bowl(client):
    payload = {
        "customer": {"name": "Ananya", "phone": "9876543210"},
        "items": [
            {
                "product_id": "CB001",
                "quantity": 1,
                "customization": {
                    "flavor": "Chocolate",
                    "filling": "Nutella",
                    "toppings": ["Brownie pieces", "Nuts"],
                    "sauce": "Caramel",
                    "message": "Happy Birthday Teja!"
                }
            }
        ],
        "pickup_time": "19:30"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    order = data["data"]
    customization = order["items"][0]["customization"]
    assert customization is not None
    assert customization["flavor"] == "Chocolate"
    assert customization["filling"] == "Nutella"
    assert "Brownie pieces" in customization["toppings"]
    assert customization["message"] == "Happy Birthday Teja!"
    assert "BOX" in customization["note"]


# Test 13: Customization on brownie rejected
def test_customization_on_brownie_rejected(client):
    payload = {
        "customer": {"name": "Test User", "phone": "9876543210"},
        "items": [
            {
                "product_id": "BR001",
                "quantity": 1,
                "customization": {
                    "flavor": "Chocolate",
                    "toppings": ["Nuts"]
                }
            }
        ],
        "pickup_time": "18:00"
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CUSTOMIZATION"
    assert "Brownie" in data["error"]["message"]


# Test 14: Order ID generation format and uniqueness
def test_order_id_generation(client):
    payload = {
        "customer": {"name": "User One", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    r1 = client.post("/api/orders", json=payload)
    r2 = client.post("/api/orders", json=payload)
    id1 = r1.json()["data"]["order_id"]
    id2 = r2.json()["data"]["order_id"]
    assert id1 != id2
    assert len(id1) == 14  # DD (2) + 8 digits date + 4 digits seq = 14
    assert len(id2) == 14


# Test 15 & 16: Pickup PIN generation and Retrieve order (PIN masked and phone masked)
def test_retrieve_order_masks_pin(client):
    payload = {
        "customer": {"name": "Sita", "phone": "9876543210"},
        "items": [{"product_id": "CB002", "quantity": 1}],
        "pickup_time": "18:00"
    }
    created_res = client.post("/api/orders", json=payload)
    created_order = created_res.json()["data"]
    order_id = created_order["order_id"]
    assert "pickup_pin" in created_order

    # Lookup order
    lookup_res = client.get(f"/api/orders/{order_id}")
    assert lookup_res.status_code == 200
    lookup_order = lookup_res.json()["data"]
    assert "pickup_pin" not in lookup_order  # Must be masked for security
    assert lookup_order["order_id"] == order_id
    assert lookup_order["customer"]["phone"] == "******3210"  # Masked phone


# Test 17: Order status endpoint
def test_order_status_endpoint(client):
    payload = {
        "customer": {"name": "Kiran", "phone": "9876543210"},
        "items": [{"product_id": "CB004", "quantity": 1}],
        "pickup_time": "19:00"
    }
    created_res = client.post("/api/orders", json=payload)
    order_id = created_res.json()["data"]["order_id"]

    status_res = client.get(f"/api/orders/{order_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["order_id"] == order_id
    assert status_data["status"] == "PENDING_PAYMENT"
    assert status_data["pickup_time"] == "19:00"


# Test 18 & 19: Pickup with correct PIN vs incorrect PIN & strict state check
def test_pickup_verification(client):
    payload = {
        "customer": {"name": "Gopal", "phone": "9876543210"},
        "items": [{"product_id": "CB005", "quantity": 1}],
        "pickup_time": "20:00"
    }
    res = client.post("/api/orders", json=payload)
    order_data = res.json()["data"]
    order_id = order_data["order_id"]
    pin = order_data["pickup_pin"]

    store_headers = {"X-Store-Token": "dd-store-secret-2026"}

    # 1. Attempt pickup while still PENDING_PAYMENT (must fail)
    pickup_fail = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert pickup_fail.status_code == 400
    assert pickup_fail.json()["error"]["code"] == "INVALID_ORDER_STATE"

    # 2. Store updates status: PENDING_PAYMENT -> CONFIRMED -> PREPARING -> READY_FOR_PICKUP
    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=store_headers)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=store_headers)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=store_headers)

    # 3. Attempt pickup with wrong PIN
    wrong_pin_res = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": "0000"})
    assert wrong_pin_res.status_code == 400
    assert wrong_pin_res.json()["error"]["code"] == "INVALID_PICKUP_PIN"

    # 4. Attempt pickup with correct PIN
    correct_pin_res = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert correct_pin_res.status_code == 200
    assert correct_pin_res.json()["data"]["status"] == "PICKED_UP"

    # 5. Order is now PICKED_UP; subsequent pickup attempt should fail
    subsequent_pickup = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert subsequent_pickup.status_code == 400
    assert subsequent_pickup.json()["error"]["code"] == "INVALID_ORDER_STATE"


# Test 20: Cancellation within 5 minutes (Full Refund)
def test_cancellation_within_5_minutes(client):
    payload = {
        "customer": {"name": "Lalitha", "phone": "9876543210"},
        "items": [{"product_id": "CB006", "quantity": 2}],
        "pickup_time": "20:30"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()["data"]
    assert cancel_data["status"] == "CANCELLED"
    cancellation = cancel_data["cancellation"]
    assert cancellation["cancelled"] is True
    assert cancellation["refund_status"] == "FULL_REFUND"
    assert cancellation["refund_amount"] == 178.0  # 89 * 2


# Test 21 & 22: Cancellation after 5 minutes (Manual Review Required, no fabricated percentage)
def test_cancellation_after_5_minutes(client, setup_mock_db):
    payload = {
        "customer": {"name": "Venkatesh", "phone": "9876543210"},
        "items": [{"product_id": "CB007", "quantity": 1}],
        "pickup_time": "21:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    # Simulate 10 minutes elapsed
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    setup_mock_db.orders.update_one({"order_id": order_id}, {"$set": {"created_at": past_time}})

    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()["data"]
    assert cancel_data["status"] == "CANCELLED"
    cancellation = cancel_data["cancellation"]
    assert cancellation["cancelled"] is True
    assert cancellation["refund_status"] == "MANUAL_REVIEW_REQUIRED"
    assert cancellation["refund_amount"] is None  # Never fabricated


# Test Cash payment status (TBD workflow)
def test_cash_payment_status(client):
    payload = {
        "customer": {"name": "Suresh", "phone": "9876543210"},
        "items": [{"product_id": "CB008", "quantity": 1}],
        "pickup_time": "21:00",
        "payment": {"method": "CASH"}
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201
    order = res.json()["data"]
    assert order["payment"]["method"] == "CASH"
    assert order["payment"]["status"] == "PENDING"


# =====================================================================
# HARDENING REGRESSION TESTS
# =====================================================================

STORE_HEADERS = {"X-Store-Token": "dd-store-secret-2026"}


def test_regression_client_cannot_control_payment_status(client):
    """1. Client payment.status cannot control payment state."""
    payload = {
        "customer": {"name": "Tamper Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00",
        "payment": {"method": "UPI", "status": "PAID"}  # Client tries to force PAID
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["payment"]["status"] == "PENDING"
    assert data["status"] == "PENDING_PAYMENT"


def test_regression_new_upi_order_starts_pending_payment(client):
    """2. New UPI order starts PENDING_PAYMENT/PENDING."""
    payload = {
        "customer": {"name": "UPI User", "phone": "9876543210"},
        "items": [{"product_id": "CB002", "quantity": 1}],
        "pickup_time": "18:00",
        "payment": {"method": "UPI"}
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["payment"]["method"] == "UPI"
    assert data["payment"]["status"] == "PENDING"
    assert data["status"] == "PENDING_PAYMENT"


def test_regression_client_price_and_subtotal_ignored(client):
    """3 & 4. Client price and subtotal cannot manipulate total."""
    payload = {
        "customer": {"name": "Spoof Price", "phone": "9876543210"},
        "items": [{
            "product_id": "CB003",  # Catalog price 99
            "quantity": 2,
            "price": 0.5,
            "subtotal": 1.0
        }],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["items"][0]["unit_price"] == 99.0
    assert data["items"][0]["subtotal"] == 198.0
    assert data["total_amount"] == 198.0


def test_regression_preparing_to_picked_up_rejected(client):
    """5. PREPARING -> PICKED_UP is rejected."""
    payload = {
        "customer": {"name": "State Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    # Advance to PREPARING
    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)

    # Attempt PREPARING -> PICKED_UP directly
    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "PICKED_UP"}, headers=STORE_HEADERS)
    assert patch_res.status_code == 400
    assert patch_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_regression_preparing_to_ready_for_pickup_works(client):
    """6. PREPARING -> READY_FOR_PICKUP works with valid store token."""
    payload = {
        "customer": {"name": "State Test 2", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    res_ready = client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)
    assert res_ready.status_code == 200
    assert res_ready.json()["data"]["status"] == "READY_FOR_PICKUP"


def test_regression_ready_to_picked_up_only_through_pickup(client):
    """7. READY_FOR_PICKUP -> PICKED_UP only through pickup endpoint."""
    payload = {
        "customer": {"name": "Pickup Only Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]
    pin = res.json()["data"]["pickup_pin"]

    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)

    # PATCH to PICKED_UP must be rejected
    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "PICKED_UP"}, headers=STORE_HEADERS)
    assert patch_res.status_code == 400
    assert patch_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    # POST to /pickup with correct PIN succeeds
    pickup_res = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert pickup_res.status_code == 200
    assert pickup_res.json()["data"]["status"] == "PICKED_UP"


def test_regression_pickup_wrong_pin_fails(client):
    """8. Wrong pickup PIN fails."""
    payload = {
        "customer": {"name": "Pin Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)

    wrong_res = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": "9999"})
    assert wrong_res.status_code == 400
    assert wrong_res.json()["error"]["code"] == "INVALID_PICKUP_PIN"


def test_regression_correct_pin_while_not_ready_fails(client):
    """10. Correct PIN while order is not READY_FOR_PICKUP fails."""
    payload = {
        "customer": {"name": "Not Ready Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]
    pin = res.json()["data"]["pickup_pin"]

    # When PENDING_PAYMENT
    res1 = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "INVALID_ORDER_STATE"

    # When PREPARING
    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    res2 = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "INVALID_ORDER_STATE"


def test_regression_picked_up_order_cannot_be_cancelled(client):
    """11. Picked-up order cannot be cancelled."""
    payload = {
        "customer": {"name": "Cancel Picked Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]
    pin = res.json()["data"]["pickup_pin"]

    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)
    client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})

    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 400
    assert cancel_res.json()["error"]["code"] == "ORDER_ALREADY_PICKED_UP"


def test_regression_already_cancelled_order_cannot_be_cancelled(client):
    """12. Already-cancelled order cannot be cancelled."""
    payload = {
        "customer": {"name": "Double Cancel", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    # First cancel
    r1 = client.post(f"/api/orders/{order_id}/cancel")
    assert r1.status_code == 200

    # Second cancel
    r2 = client.post(f"/api/orders/{order_id}/cancel")
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "ORDER_ALREADY_CANCELLED"


def test_regression_public_get_order_does_not_expose_pickup_pin(client):
    """19. Public GET order does not expose pickup_pin."""
    payload = {
        "customer": {"name": "PIN Mask Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    lookup = client.get(f"/api/orders/{order_id}")
    assert lookup.status_code == 200
    assert "pickup_pin" not in lookup.json()["data"]


def test_regression_public_get_order_masks_customer_phone(client):
    """20. Public GET order masks phone."""
    payload = {
        "customer": {"name": "Phone Mask Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    lookup = client.get(f"/api/orders/{order_id}")
    assert lookup.status_code == 200
    assert lookup.json()["data"]["customer"]["phone"] == "******3210"


def test_regression_patch_status_response_does_not_expose_pickup_pin(client):
    """21. PATCH status response does not expose pickup_pin."""
    payload = {
        "customer": {"name": "Patch Pin Mask", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    assert patch_res.status_code == 200
    assert "pickup_pin" not in patch_res.json()["data"]


def test_regression_invalid_status_transition_returns_error_code(client):
    """22. Invalid status transitions return INVALID_STATUS_TRANSITION."""
    payload = {
        "customer": {"name": "Transition Error Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    # Skip: PENDING_PAYMENT -> READY_FOR_PICKUP
    skip_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)
    assert skip_res.status_code == 400
    assert skip_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_regression_patch_status_without_token_returns_401(client):
    """23. PATCH status without X-Store-Token returns 401."""
    payload = {
        "customer": {"name": "No Auth Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    no_auth_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"})
    assert no_auth_res.status_code == 401
    assert no_auth_res.json()["error"]["code"] == "UNAUTHORIZED_STORE_ACCESS"


def test_regression_patch_status_with_invalid_token_returns_401(client):
    """24. PATCH status with invalid X-Store-Token returns 401."""
    payload = {
        "customer": {"name": "Bad Auth Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    bad_auth_res = client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "CONFIRMED"},
        headers={"X-Store-Token": "wrong-secret"}
    )
    assert bad_auth_res.status_code == 401
    assert bad_auth_res.json()["error"]["code"] == "UNAUTHORIZED_STORE_ACCESS"


def test_regression_invalid_order_id_returns_not_found(client):
    """26. Invalid order ID returns ORDER_NOT_FOUND."""
    res = client.get("/api/orders/NONEXISTENT1234")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "ORDER_NOT_FOUND"

    res_cancel = client.post("/api/orders/NONEXISTENT1234/cancel")
    assert res_cancel.status_code == 404
    assert res_cancel.json()["error"]["code"] == "ORDER_NOT_FOUND"

    res_pickup = client.post("/api/orders/NONEXISTENT1234/pickup", json={"pickup_pin": "1234"})
    assert res_pickup.status_code == 404
    assert res_pickup.json()["error"]["code"] == "ORDER_NOT_FOUND"


def test_regression_pickup_time_format_validation(client):
    """27. Pickup-time format validation works."""
    payload = {
        "customer": {"name": "Time Format Test", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "not-a-valid-time"
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_PICKUP_TIME"


def test_regression_pickup_outside_store_hours_rejected(client):
    """28. Pickup outside 16:00–23:00 is rejected."""
    # Morning 10:00 AM (Store opens 4 PM / 16:00)
    payload_morning = {
        "customer": {"name": "Morning Order", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "10:00"
    }
    res1 = client.post("/api/orders", json=payload_morning)
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "STORE_CLOSED"

    # Late night 23:30 (Store closes 11 PM / 23:00)
    payload_late = {
        "customer": {"name": "Late Order", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "23:30"
    }
    res2 = client.post("/api/orders", json=payload_late)
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "STORE_CLOSED"


def test_regression_terminal_picked_up_cannot_be_modified(client):
    """29. Terminal PICKED_UP cannot be modified."""
    payload = {
        "customer": {"name": "Terminal Picked", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]
    pin = res.json()["data"]["pickup_pin"]

    client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=STORE_HEADERS)
    client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pin})

    # Attempt to change status after PICKED_UP
    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=STORE_HEADERS)
    assert patch_res.status_code == 400
    assert patch_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_regression_terminal_cancelled_cannot_be_modified(client):
    """30. Terminal CANCELLED cannot be modified."""
    payload = {
        "customer": {"name": "Terminal Cancelled", "phone": "9876543210"},
        "items": [{"product_id": "CB001", "quantity": 1}],
        "pickup_time": "18:00"
    }
    res = client.post("/api/orders", json=payload)
    order_id = res.json()["data"]["order_id"]

    client.post(f"/api/orders/{order_id}/cancel")

    # Attempt to change status after CANCELLED
    patch_res = client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=STORE_HEADERS)
    assert patch_res.status_code == 400
    assert patch_res.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
