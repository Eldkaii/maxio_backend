from sqlalchemy.orm import Session
from src.utils.logger_config import test_logger as logger
from fastapi.testclient import TestClient
from src.test.utils_common_methods import TestUtils

utils = TestUtils()


def test_login_success(client: TestClient):
    utils.create_player(client, username="alice")

    response = client.post("/auth/login", json={
        "username": "alice",
        "password": "testpass"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    utils.create_player(client, username="alice")

    response = client.post("/auth/login", json={
        "username": "alice",
        "password": "wrongpass"
    })

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


def test_me_endpoint_with_valid_token(client: TestClient):
    utils.create_player(client, username="alice")

    login = client.post("/auth/login", json={
        "username": "alice",
        "password": "testpass"
    })
    token = login.json()["access_token"]

    response = client.get("/maxio/users/me", headers={
        "Authorization": f"Bearer {token}"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"


def test_me_endpoint_without_token(client: TestClient):
    response = client.get("/maxio/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_me_endpoint_with_invalid_token(client: TestClient):
    response = client.get("/maxio/users/me", headers={
        "Authorization": "Bearer faketoken123"
    })

    assert response.status_code == 401
    assert "Token inválido" in response.json()["detail"]