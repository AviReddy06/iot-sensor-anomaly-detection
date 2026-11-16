"""
e2e_tests/test_tier1_features/test_area01_api_contracts.py
Area 1: API Contracts & Schema Integrity (Features 2, 3)
Tier 1 Tests: Happy-path schema conformance, status codes, and error formats.
"""

import pytest
from starlette.testclient import TestClient
from backend.schemas.client_schemas import ClientStatusResponse, ClientReading, ClientEvent


BANNED_ML_TERMS = [
    "isolation", "forest", "score", "threshold", "z-score", "precision",
    "recall", "f1", "confusion", "ewma", "hardware", "serial", "websocket",
    "port", "baud", "model", "cockpit"
]


def test_a1_t1_01_client_status_schema_conformance(client: TestClient):
    """
    TEST-A1-T1-01: GET /api/client/status schema conformance and banned terms absence.
    """
    response = client.get("/api/client/status")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Validate against Pydantic schema
    validated = ClientStatusResponse.model_validate(data)
    assert validated.status in ["Live", "Simulated", "Offline", "normal", "live", "simulated", "offline"]
    assert isinstance(validated.active_unusual_reading, bool)
    assert isinstance(validated.headline, str)
    assert isinstance(validated.supporting_text, str)

    # Check banned terms in client status response keys and values
    import re
    for k, v in data.items():
        k_lower = k.lower()
        v_str = str(v).lower()
        for term in BANNED_ML_TERMS:
            # Match whole word to avoid false positives on 'supporting_text' containing 'port'
            pattern = rf"\b{re.escape(term)}\b"
            assert not re.search(pattern, k_lower), f"Banned ML term '{term}' leaked in key '{k}'"
            # Note: headline and text should not contain raw ML jargon
            if k in ["headline", "supporting_text"]:
                assert not re.search(pattern, v_str), f"Banned ML term '{term}' leaked in {k}: '{v}'"


def test_a1_t1_02_client_readings_schema_conformance(client: TestClient):
    """
    TEST-A1-T1-02: GET /api/client/readings?limit=10 schema conformance.
    """
    response = client.get("/api/client/readings?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10

    for item in data:
        reading = ClientReading.model_validate(item)
        assert isinstance(reading.temperature, (int, float))
        assert isinstance(reading.humidity, (int, float))
        # Ensure no technical scoring fields leaked
        assert not hasattr(reading, "iforest_score")
        assert not hasattr(reading, "z_score")


def test_a1_t1_03_client_events_schema_conformance(client: TestClient):
    """
    TEST-A1-T1-03: GET /api/client/events?limit=5 schema conformance.
    """
    response = client.get("/api/client/events?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

    for item in data:
        event = ClientEvent.model_validate(item)
        assert event.severity in ["Low", "Medium", "High"]
        assert isinstance(event.sentence, str)


def test_a1_t1_04_admin_auth_login_contract(client: TestClient, admin_password: str):
    """
    TEST-A1-T1-04: POST /api/auth/login contract with valid credentials.
    """
    response = client.post("/api/auth/login", json={"password": admin_password})
    assert response.status_code == 200
    data = response.json()

    assert "token" in data
    assert isinstance(data["token"], str) and len(data["token"]) > 10
    assert data.get("token_type") == "bearer"
    assert data.get("expires_in_seconds") == 28800
    # Crucial security check: password must not be reflected
    assert admin_password not in response.text


def test_a1_t1_05_admin_model_details_schema_conformance(client: TestClient, admin_token: str):
    """
    TEST-A1-T1-05: GET /api/admin/model/details with Bearer token.
    """
    response = client.get(
        "/api/admin/model/details",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "version" in data
    assert "feature_cols" in data
    assert isinstance(data["feature_cols"], list)
    assert len(data["feature_cols"]) == 12
    assert "sensitivity_thresholds" in data
    assert "Low" in data["sensitivity_thresholds"]
    assert "Medium" in data["sensitivity_thresholds"]
    assert "High" in data["sensitivity_thresholds"]


def test_a1_t1_06_uniform_error_response_structure_on_404(client: TestClient):
    """
    TEST-A1-T1-06: Uniform error response structure on unmapped /api/* route.
    Must never return raw stack traces or internal filesystem paths.
    """
    response = client.get("/api/nonexistent_contract_test_route_404")
    assert response.status_code == 404
    assert response.headers.get("content-type", "").startswith("application/json")
    data = response.json()
    assert "detail" in data
    error_str = str(data["detail"])
    assert "Traceback (most recent call last)" not in error_str
    assert "backend\\" not in error_str
    assert "backend/" not in error_str
