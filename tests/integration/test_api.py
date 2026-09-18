import json
from pathlib import Path
import pytest
import mongomock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.connection import set_test_database


@pytest.fixture(autouse=True)
def setup_integration_db():
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["integration_dd_house"]
    set_test_database(mock_db)

    # Seed products
    seed_file = Path(__file__).resolve().parent.parent.parent / "database" / "seed" / "products.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    mock_db.products.insert_many(products)

    yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


def test_complete_customer_journey(client):
    """
    Test entire flow:
    1. Check health
    2. Browse products
    3. Create order
    4. Verify server-side total
    5. Check tracking status
    6. Masked PIN in public lookup
    7. Ready for pickup -> verify pickup with PIN
    """
    # 1. Health
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    # 2. Browse products
    prod_res = client.get("/api/products")
    assert prod_res.status_code == 200
    products = prod_res.json()["data"]
    assert len(products) == 12

    # 3. Create order with Cake Bowl + Brownie
    order_payload = {
        "customer": {"name": "Swathi", "phone": "9848022338"},
        "items": [
            {
                "product_id": "CB004",  # Choco Truffle: 99
                "quantity": 1,
                "customization": {
                    "flavor": "Chocolate",
                    "filling": "Nutella",
                    "toppings": ["Oreo pieces"],
                    "sauce": "Nutella",
                    "message": "Best Wishes!"
                }
            },
            {
                "product_id": "BR002",  # Choco-Chip Brownie: 50
                "quantity": 2
            }
        ],
        "pickup_time": "18:30",
        "payment": {"method": "UPI"}
    }
    create_res = client.post("/api/orders", json=order_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()["data"]
    order_id = created_data["order_id"]
    pickup_pin = created_data["pickup_pin"]

    # 4. Total = 99 + (50 * 2) = 199, UPI starts as PENDING_PAYMENT
    assert created_data["total_amount"] == 199.0
    assert created_data["status"] == "PENDING_PAYMENT"
    assert created_data["payment"]["status"] == "PENDING"

    # 5. Check tracking status
    status_res = client.get(f"/api/orders/{order_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["data"]["status"] == "PENDING_PAYMENT"

    # 6. Lookup order - verify pickup_pin is excluded and customer phone is masked
    lookup_res = client.get(f"/api/orders/{order_id}")
    assert lookup_res.status_code == 200
    assert "pickup_pin" not in lookup_res.json()["data"]
    assert lookup_res.json()["data"]["customer"]["phone"] == "******2338"

    # 7. Store advances order step-by-step using store token
    store_headers = {"X-Store-Token": "dd-store-secret-2026"}
    # PENDING_PAYMENT -> CONFIRMED
    res1 = client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=store_headers)
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "CONFIRMED"
    assert "pickup_pin" not in res1.json()["data"]

    # CONFIRMED -> PREPARING
    res2 = client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"}, headers=store_headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "PREPARING"

    # PREPARING -> READY_FOR_PICKUP
    res3 = client.patch(f"/api/orders/{order_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=store_headers)
    assert res3.status_code == 200
    assert res3.json()["data"]["status"] == "READY_FOR_PICKUP"

    # 8. Customer arrives and presents PIN for pickup
    pickup_res = client.post(f"/api/orders/{order_id}/pickup", json={"pickup_pin": pickup_pin})
    assert pickup_res.status_code == 200
    assert pickup_res.json()["data"]["status"] == "PICKED_UP"


def test_cancellation_refund_rules(client):
    """Test full refund within 5 minutes."""
    order_payload = {
        "customer": {"name": "Ramesh", "phone": "9848011223"},
        "items": [{"product_id": "CL002", "quantity": 3}],  # 30 * 3 = 90
        "pickup_time": "19:00"
    }
    create_res = client.post("/api/orders", json=order_payload)
    order_id = create_res.json()["data"]["order_id"]

    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["cancellation"]["refund_status"] == "FULL_REFUND"
    assert cancel_res.json()["data"]["cancellation"]["refund_amount"] == 90.0
