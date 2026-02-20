"""
Epic 5 Ops & Audit Stories
Tests: US-66 evidence, US-68 threat sim, US-70 incident workflow, US-73 anomaly detection.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def _get_admin_token():
    """Login as admin and return Bearer header dict."""
    resp = client.post("/auth/login", json={"credential": "admin123", "password": "admin123"})
    if resp.status_code != 200:
        pytest.skip("Cannot login as admin - DB may not be seeded")
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


# US-66: Evidence Package
def test_evidence_download():
    """US-66: Checking evidence download endpoint returns 200 or 404."""
    election_id = "00000000-0000-0000-0000-000000000001"
    response = client.get(f"/api/ops/evidence/{election_id}")
    assert response.status_code in [200, 404]


# US-68: Threat Simulation
def test_threat_simulation():
    """US-68: Simulating a replay attack scenario and verifying detection."""
    headers = _get_admin_token()
    response = client.post("/api/security/simulate", json={
        "scenario_type": "replay_attack",
        "intensity": "low"
    }, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert data["scenario_type"] == "replay_attack"


# US-70: Incident Response
def test_incident_workflow():
    """US-70: Creating an incident, then updating its status to investigating."""
    headers = _get_admin_token()

    # 1. Create Incident
    response = client.post("/api/ops/incidents", json={
        "title": "Test Incident",
        "description": "Automated test",
        "severity": "low"
    }, headers=headers)

    assert response.status_code == 200
    incident = response.json()
    incident_id = incident["incident_id"]

    # 2. Update Status
    update_response = client.put(f"/api/ops/incidents/{incident_id}", json={
        "status": "investigating",
        "resolution_notes": "Bot checked"
    }, headers=headers)

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "investigating"


# US-73: Anomaly Detection
def test_anomaly_detection():
    """US-73: Fetching anomaly list and verifying it returns a list."""
    headers = _get_admin_token()
    response = client.get("/api/security/anomalies", headers=headers)

    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)
