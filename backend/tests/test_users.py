"""User management endpoint tests."""

import pytest


def test_list_users(client, auth_headers):
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_create_user(client, auth_headers):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newanalyst@test.com",
            "password": "Analyst@1234",
            "full_name": "New Analyst",
            "role": "analyst",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["email"] == "newanalyst@test.com"
    assert data["role"] == "analyst"


def test_create_duplicate_user(client, auth_headers):
    payload = {
        "email": "dup@test.com",
        "password": "Password@1234",
        "full_name": "Dup User",
        "role": "viewer",
    }
    client.post("/api/v1/users", json=payload, headers=auth_headers)
    response = client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert response.status_code in (400, 409)
