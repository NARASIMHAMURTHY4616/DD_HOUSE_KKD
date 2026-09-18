import json
from pathlib import Path
import pytest
import mongomock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.connection import set_test_database


@pytest.fixture(autouse=True)
def setup_mock_db():
    # Use mongomock to simulate MongoDB in-memory
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["test_dd_house"]
    set_test_database(mock_db)

    # Load and seed products
    seed_file = Path(__file__).resolve().parent.parent.parent.parent / "database" / "seed" / "products.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    mock_db.products.insert_many(products)

    yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "healthy"
    assert data["store"]["phone"] == "7013522727"


def test_get_all_products(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 12
    product_ids = [p["product_id"] for p in data["data"]]
    assert "CB001" in product_ids
    assert "BR001" in product_ids
    assert "CL001" in product_ids


def test_get_products_by_category(client):
    response = client.get("/api/products?category=Cake%20Bowl")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 8
    for item in data["data"]:
        assert item["category"] == "Cake Bowl"


def test_get_product_by_id_success(client):
    response = client.get("/api/products/CB003")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    product = data["data"]
    assert product["product_id"] == "CB003"
    assert product["name"] == "Triple Chocolate"
    assert product["price"] == 99.0
    assert product["customizable"] is True


def test_get_product_by_id_not_found(client):
    response = client.get("/api/products/CB999")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "PRODUCT_NOT_FOUND"
