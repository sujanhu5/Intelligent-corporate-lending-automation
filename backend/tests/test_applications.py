"""Application CRUD endpoint tests."""

import pytest


@pytest.fixture()
def company_for_app(client, auth_headers):
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "App Test Company",
            "registration_number": "APP-TEST-001",
            "company_type": "private_limited",
            "industry": "technology",
            "contact_email": "app@test.com",
            "registered_address": "789 App Street",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture()
def sample_application(client, auth_headers, company_for_app):
    response = client.post(
        "/api/v1/applications",
        json={
            "company_id": company_for_app["id"],
            "loan_amount_requested": 500000,
            "loan_tenure_months": 36,
            "loan_purpose": "working_capital",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_create_application(sample_application):
    assert sample_application["loan_amount_requested"] == 500000
    assert sample_application["loan_tenure_months"] == 36
    assert sample_application["status"] == "draft"
    assert sample_application["application_number"].startswith("CLA-")


def test_list_applications(client, auth_headers, sample_application):
    response = client.get("/api/v1/applications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_application(client, auth_headers, sample_application):
    aid = sample_application["id"]
    response = client.get(f"/api/v1/applications/{aid}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == aid


def test_filter_by_status(client, auth_headers, sample_application):
    response = client.get("/api/v1/applications?status=draft", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["status"] == "draft"


def test_create_application_unauthenticated(client):
    response = client.post("/api/v1/applications", json={})
    assert response.status_code == 401
