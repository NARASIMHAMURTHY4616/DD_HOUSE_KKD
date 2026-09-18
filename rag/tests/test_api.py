"""Integration tests for DD House RAG FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from rag.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/rag/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["indexed_chunks"] > 0

def test_conflicts_endpoint():
    response = client.get("/api/rag/conflicts")
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert len(data["conflicts"]) >= 5
    # Check phone conflict
    phone_conflict = next(c for c in data["conflicts"] if c["field"] == "phone")
    assert phone_conflict["business_provided"] == "7013522727"
    assert phone_conflict["external_reference"] == "9948732532"
    assert phone_conflict["customer_answer"] == "7013522727"

def test_chat_triple_chocolate_price():
    response = client.post("/api/rag/chat", json={"question": "How much is the Triple Chocolate cake bowl?"})
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "99" in data["answer"]
    assert len(data["sources"]) > 0

def test_chat_brownie_customization_denied():
    response = client.post("/api/rag/chat", json={"question": "Can I customize brownies?"})
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "cannot" in data["answer"].lower()

def test_chat_delivery_policy():
    response = client.post("/api/rag/chat", json={"question": "Do you offer delivery?"})
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert "pickup rather than delivery" in data["answer"].lower() or "store pickup" in data["answer"].lower()

def test_chat_unknown_hyderabad_delivery():
    response = client.post("/api/rag/chat", json={"question": "Do you deliver to Hyderabad?"})
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is False
    assert "7013522727" in data["answer"]

def test_chat_allergen_eggless():
    response = client.post("/api/rag/chat", json={"question": "Are all products eggless?"})
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is False
    assert "7013522727" in data["answer"] or "verified information" in data["answer"].lower()
