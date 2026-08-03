import os

os.environ["DATABASE_URL"] = "sqlite:///./test_ai_fatah.db"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_storefront() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/")
        assert response.status_code == 200
        assert "Fresh groceries" in response.text


def test_products_api_starts_empty() -> None:
    with TestClient(app) as client:
        response = client.get("/api/products")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
