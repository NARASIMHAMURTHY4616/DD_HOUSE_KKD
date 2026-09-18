from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx

from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_forwarding_success(client):
    mock_rag_response = httpx.Response(
        status_code=200,
        json={"response": "Triple Chocolate cake bowl is priced at Rs. 99 and is available every day."}
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_rag_response
        response = client.post("/api/chat", json={"message": "How much is Triple Chocolate?"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "99" in data["data"]["response"]
        assert data["data"]["source"] == "rag"


def test_chat_forwarding_service_unavailable(client):
    """
    When RAG service is unreachable, backend must return RAG_SERVICE_UNAVAILABLE
    and NEVER fabricate answers.
    """
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        response = client.post("/api/chat", json={"message": "What are the shop hours?"})
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "RAG_SERVICE_UNAVAILABLE"
        assert "unavailable" in data["error"]["message"].lower()
        assert "7013522727" in data["error"]["message"]


def test_chat_empty_message_rejected(client):
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
