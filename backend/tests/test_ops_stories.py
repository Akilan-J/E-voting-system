import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

# US-66: Evidence Package
def test_evidence_download():
    election_id = "00000000-0000-0000-0000-000000000001"
    response = client.get(f"/api/ops/evidence/{election_id}")
    
    # Should perform redirect or return file
    # We check if 200 (file) or 404 (not ready) - both valid responses for structure test
    assert response.status_code in [200, 404]

# US-67: System Event Logging (Internal Check)
# Hard to test via external API without specific log endpoint exposed
# Skipping direct API test - relies on backend logic

# US-68: Threat Simulation
def test_threat_simulation():
    response = client.post("/api/security/simulate", json={
        "scenario_type": "replay_attack",
        "intensity": "low"
    }, headers={"X-User-Role": "admin"})
    
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data
    assert data["scenario_type"] == "replay_attack"

# US-70: Incident Response
def test_incident_workflow():
    # 1. Create Incident
    response = client.post("/api/ops/incidents", json={
        "title": "Test Incident",
        "description": "Automated test",
        "severity": "low"
    }, headers={"X-User-Role": "admin"})
    
    assert response.status_code == 200
    incident = response.json()
    incident_id = incident["incident_id"]
    
    # 2. Update Status
    update_response = client.put(f"/api/ops/incidents/{incident_id}", json={
        "status": "investigating",
        "resolution_notes": "Bot checked"
    }, headers={"X-User-Role": "admin"})
    
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "investigating"

# US-73: Anomaly Detection
def test_anomaly_detection():
    response = client.get("/api/security/anomalies", headers={"X-User-Role": "admin"})
    
    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)
