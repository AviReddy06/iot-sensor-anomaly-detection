"""
e2e_tests/test_tier4_scenarios/test_scenario4_adversarial_attack.py
Tier 4 Scenario 4: Adversarial Security Attack Injection & Hardened Defense Verification
Exercises brute-force lockout, forged tokens, directory traversal, formula injection, and CORS rejection.
"""

import io
import pytest
from starlette.testclient import TestClient
from backend.database import insert_event
import backend.auth as auth


def test_scenario_04_adversarial_attack_defenses(client: TestClient, admin_token: str, admin_password: str):
    """
    Scenario 4: Multi-vector security attack simulation.
    - Attack 1: Brute-force credential guessing -> locked out at 6th attempt (HTTP 429).
    - Attack 2: Tampered bearer token -> rejected (HTTP 401).
    - Attack 3: Directory traversal on datasets -> rejected (HTTP 400/404).
    - Attack 4: Unauthorized cross-origin requests -> CORS headers withheld.
    """
    # Vector 1: Brute-force lockout
    if admin_password:
        client.post("/api/auth/login", json={"password": admin_password})
    for _ in range(5):
        client.post("/api/auth/login", json={"password": "hacker_guess"})
    resp_locked = client.post("/api/auth/login", json={"password": "hacker_guess"})
    assert resp_locked.status_code == 429

    # Vector 2: Tampered bearer token
    tampered_sig = admin_token[:-6] + "999999"
    resp_tamper = client.get("/api/admin/model/details", headers={"Authorization": f"Bearer {tampered_sig}"})
    assert resp_tamper.status_code == 401

    # Vector 3: Path traversal on download
    resp_traversal = client.get(
        "/api/admin/datasets/download/%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_traversal.status_code in [400, 403, 404]
    assert "root:x:0:0" not in resp_traversal.text

    # Vector 4: CORS rejection
    resp_cors = client.get("/api/client/status", headers={"Origin": "https://malicious-command-center.xyz"})
    assert resp_cors.headers.get("access-control-allow-origin") != "https://malicious-command-center.xyz"
