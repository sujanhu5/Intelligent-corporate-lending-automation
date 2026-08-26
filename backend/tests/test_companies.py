"""Company CRUD endpoint tests."""

import pytest


@pytest.fixture()
def sample_company(client, auth_headers):
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Test Corp Sdn Bhd",
            "registration_number": "TEST-001",
            "contact_email": "info@testcorp.com",
            "registered_address": "123 Test Street",
            "company_type": "private_limited",
            "industry": "technology",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201)
    return response.json()


def test_create_company(sample_company):
    assert sample_company["name"] == "Test Corp Sdn Bhd"
    assert sample_company["registration_number"] == "TEST-001"
    assert sample_company["status"] == "active"


def test_list_companies(client, auth_headers, sample_company):
    response = client.get("/api/v1/companies", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_company(client, auth_headers, sample_company):
    cid = sample_company["id"]
    response = client.get(f"/api/v1/companies/{cid}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == cid


def test_update_company(client, auth_headers, sample_company):
    cid = sample_company["id"]
    response = client.put(
        f"/api/v1/companies/{cid}",
        json={"name": "Updated Corp", "registration_number": "TEST-001",
              "contact_email": "new@testcorp.com", "registered_address": "456 New Street"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Corp"


def test_search_companies(client, auth_headers, sample_company):
    response = client.get("/api/v1/companies?search=Test", headers=auth_headers)
    assert response.status_code == 200


def test_create_company_unauthenticated(client):
    response = client.post("/api/v1/companies", json={"name": "Fail"})
    assert response.status_code == 401
