"""Rule CRUD API endpoint tests."""

import pytest


@pytest.fixture()
def sample_rule(client, auth_headers):
    response = client.post(
        "/api/v1/rules",
        json={
            "name": "Test Current Ratio Rule",
            "metric_field": "current_ratio",
            "operator": "gte",
            "threshold": 1.0,
            "category": "liquidity",
            "action": "reject",
            "is_mandatory": True,
            "priority": 100,
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201)
    return response.json()


def test_create_rule(sample_rule):
    assert sample_rule["name"] == "Test Current Ratio Rule"
    assert sample_rule["is_mandatory"] is True
    assert sample_rule["is_active"] is True


def test_list_rules(client, auth_headers, sample_rule):
    response = client.get("/api/v1/rules", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_toggle_rule(client, auth_headers, sample_rule):
    rid = sample_rule["id"]
    response = client.post(f"/api/v1/rules/{rid}/toggle", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = client.post(f"/api/v1/rules/{rid}/toggle", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_update_rule(client, auth_headers, sample_rule):
    rid = sample_rule["id"]
    response = client.put(
        f"/api/v1/rules/{rid}",
        json={
            "name": "Updated Rule",
            "metric_field": "quick_ratio",
            "operator": "gte",
            "threshold": 0.5,
            "category": "liquidity",
            "action": "manual_review",
            "is_mandatory": False,
            "priority": 50,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Rule"


def test_delete_rule(client, auth_headers, sample_rule):
    rid = sample_rule["id"]
    response = client.delete(f"/api/v1/rules/{rid}", headers=auth_headers)
    assert response.status_code in (200, 204)


def test_create_rule_unauthenticated(client):
    response = client.post("/api/v1/rules", json={"name": "Fail"})
    assert response.status_code == 401
