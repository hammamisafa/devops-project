from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_item():
    created = client.post("/items", json={"name": "Livre", "price": 12.5})
    assert created.status_code == 201
    item_id = created.json()["id"]

    fetched = client.get(f"/items/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Livre"


def test_get_unknown_item_returns_404():
    response = client.get("/items/9999")
    assert response.status_code == 404


def test_create_item_invalid_payload():
    response = client.post("/items", json={"name": "Sans prix"})
    assert response.status_code == 422


def test_delete_item():
    created = client.post("/items", json={"name": "Stylo", "price": 1.0})
    item_id = created.json()["id"]
    assert client.delete(f"/items/{item_id}").status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404