"""Authentication endpoint tests."""

import pytest


def test_login_success(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin@test.com", "password": "TestAdmin@1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin@test.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "anything"},
    )
    assert response.status_code == 401


def test_me_authenticated(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_admin@test.com"
    assert data["role"] == "admin"


def test_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_change_password(client, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "TestAdmin@1234",
            "new_password": "NewPassword@5678",
            "confirm_password": "NewPassword@5678",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test_admin@test.com", "password": "NewPassword@5678"},
    )
    assert login_resp.status_code == 200

    client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "NewPassword@5678",
            "new_password": "TestAdmin@1234",
            "confirm_password": "TestAdmin@1234",
        },
        headers=auth_headers,
    )
