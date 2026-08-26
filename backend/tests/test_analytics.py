"""Analytics endpoint tests."""

import pytest


def test_summary(client, auth_headers):
    response = client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_applications" in data
    assert "total_companies" in data


def test_trends(client, auth_headers):
    response = client.get("/api/v1/analytics/trends?months=6", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_risk_distribution(client, auth_headers):
    response = client.get("/api/v1/analytics/risk-distribution", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_industry_breakdown(client, auth_headers):
    response = client.get("/api/v1/analytics/industry-breakdown", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_loan_purpose_breakdown(client, auth_headers):
    response = client.get("/api/v1/analytics/loan-purpose-breakdown", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_pipeline_funnel(client, auth_headers):
    response = client.get("/api/v1/analytics/pipeline-funnel", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_rule_triggers(client, auth_headers):
    response = client.get("/api/v1/analytics/rule-triggers", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_pipeline_metrics(client, auth_headers):
    response = client.get("/api/v1/analytics/pipeline-metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_runs" in data


def test_analytics_unauthenticated(client):
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 401
