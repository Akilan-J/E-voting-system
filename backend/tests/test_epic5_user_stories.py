import hashlib
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, Election, EncryptedVote, ElectionResult
from app.models.ledger_models import LedgerEntry, LedgerEvent
from app.services.ledger_service import ledger_service
from app.utils.crypto_utils import MerkleTree

client = TestClient(app)


def _ensure_election(db, election_id: uuid.UUID) -> Election:
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if election:
        return election
    now = datetime.utcnow()
    election = Election(
        election_id=election_id,
        title="Test Election",
        description="Epic 5 test election",
        start_time=now,
        end_time=now + timedelta(days=1),
        status="active",
        candidates=[{"id": 1, "name": "Alice"}]
    )
    db.add(election)
    db.commit()
    db.refresh(election)
    return election


@pytest.fixture(scope="session")
def admin_token() -> str:
    response = client.post("/auth/login", json={"credential": "admin"})
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    return payload["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# US-62: Receipt Verification (verified case)

def test_epic5_receipt_verification_verified():
    election_id = uuid.uuid4()
    receipt_hash = hashlib.sha256(b"receipt").hexdigest()
    entry_hash = hashlib.sha256(b"entry").hexdigest()

    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
        vote = EncryptedVote(
            election_id=election_id,
            encrypted_vote="ciphertext",
            vote_proof="mock_proof",
            receipt_hash=receipt_hash,
            nonce=f"nonce-{uuid.uuid4()}"
        )
        db.add(vote)
        db.commit()
        db.refresh(vote)

        entry = LedgerEntry(
            election_id=election_id,
            vote_id=vote.vote_id,
            entry_hash=entry_hash,
            ciphertext_hash=hashlib.sha256(b"ciphertext").hexdigest()
        )
        db.add(entry)
        db.commit()
    finally:
        db.close()

    response = client.post("/api/verify/receipt", json={
        "receipt_hash": receipt_hash,
        "election_id": str(election_id)
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["proof"]["root"] == MerkleTree([entry_hash]).get_root()
    assert data["proof"]["index"] == 0


# US-63: ZK Proof Verification (valid bundle)

def test_epic5_zk_proof_verification_valid():
    election_id = uuid.uuid4()
    verification_hash = hashlib.sha256(b"verification").hexdigest()
    entry_hash = hashlib.sha256(b"zk-entry").hexdigest()

    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
        db.add(LedgerEntry(election_id=election_id, entry_hash=entry_hash))
        db.add(ElectionResult(
            election_id=election_id,
            final_tally={"Alice": 1},
            total_votes_tallied=1,
            verification_hash=verification_hash,
            published_at=datetime.utcnow()
        ))
        db.commit()
    finally:
        db.close()

    merkle_root = MerkleTree([entry_hash]).get_root()
    proof_hash = hashlib.sha256(
        f"{election_id}|{verification_hash}|{merkle_root}".encode()
    ).hexdigest()

    proof_bundle = {
        "election_id": str(election_id),
        "verification_hash": verification_hash,
        "ledger_root": merkle_root,
        "proof_hash": proof_hash
    }

    response = client.post("/api/verify/zk-proof", json={
        "election_id": str(election_id),
        "proof_bundle": proof_bundle
    })

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["details"]["ledger_root_match"] is True
    assert data["details"]["verification_hash_match"] is True
    assert data["details"]["proof_hash_match"] is True


# US-64: Ledger Replay Audit

def test_epic5_ledger_replay_clean():
    election_id = uuid.uuid4()

    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
        ledger_service.create_genesis(db, election_id)
    finally:
        db.close()

    response = client.post("/api/security/replay-ledger", json={
        "election_id": str(election_id),
        "verify_signatures": True
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clean"


# US-65: Transparency Dashboard

def test_epic5_transparency_dashboard():
    election_id = uuid.uuid4()
    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
    finally:
        db.close()

    response = client.get(f"/api/ops/dashboard/{election_id}")
    assert response.status_code == 200
    data = response.json()
    assert "election_status" in data
    assert "votes_cast_current" in data
    assert "turnout_percentage" in data


# US-66: Evidence Package

def test_epic5_evidence_package_download():
    election_id = uuid.uuid4()
    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
    finally:
        db.close()

    response = client.get(f"/api/ops/evidence/{election_id}")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/zip"


# US-68: Threat Simulation

def test_epic5_threat_simulation(admin_token):
    response = client.post(
        "/api/security/simulate",
        json={"scenario_type": "replay_attack", "intensity": "low"},
        headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_type"] == "replay_attack"
    assert "simulation_id" in data


# US-69/US-73: Anomaly Detection

def test_epic5_anomalies_and_report():
    response = client.get("/api/security/anomalies")
    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)

    report = client.get("/api/security/anomaly-report")
    assert report.status_code == 200
    payload = report.json()
    assert "report_hash" in payload
    assert "anomalies" in payload


# US-70: Incident Response Workflow

def test_epic5_incident_workflow(admin_token):
    create_resp = client.post(
        "/api/ops/incidents",
        json={
            "title": "Test Incident",
            "description": "Automated test incident",
            "severity": "low",
            "reported_by": "pytest"
        },
        headers=_auth_headers(admin_token)
    )
    assert create_resp.status_code == 200
    incident = create_resp.json()

    update_resp = client.put(
        f"/api/ops/incidents/{incident['incident_id']}",
        json={"status": "triage", "resolution_notes": "Initial review"},
        headers=_auth_headers(admin_token)
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "triage"

    action_resp = client.post(
        f"/api/ops/incidents/{incident['incident_id']}/actions",
        json={"action_type": "NOTE_ADDED", "details": {"note": "Checked logs"}},
        headers=_auth_headers(admin_token)
    )
    assert action_resp.status_code == 200

    report_resp = client.get(
        f"/api/ops/incidents/{incident['incident_id']}/report",
        headers=_auth_headers(admin_token)
    )
    assert report_resp.status_code == 200
    assert "report_hash" in report_resp.json()


# US-71: Dispute Resolution Workflow

def test_epic5_dispute_workflow(admin_token):
    election_id = uuid.uuid4()
    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
    finally:
        db.close()

    create_resp = client.post(
        "/api/ops/disputes",
        json={
            "title": "Test Dispute",
            "description": "Automated test dispute",
            "election_id": str(election_id),
            "filed_by": "pytest",
            "evidence": ["receipt:abc123"]
        },
        headers=_auth_headers(admin_token)
    )
    assert create_resp.status_code == 200
    dispute = create_resp.json()

    update_resp = client.put(
        f"/api/ops/disputes/{dispute['dispute_id']}",
        json={"status": "investigating", "resolution_notes": "Assigned"},
        headers=_auth_headers(admin_token)
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "investigating"

    report_resp = client.get(
        f"/api/ops/disputes/{dispute['dispute_id']}/report",
        headers=_auth_headers(admin_token)
    )
    assert report_resp.status_code == 200
    assert "report_hash" in report_resp.json()


# US-72: Compliance Report

def test_epic5_compliance_report(admin_token):
    election_id = uuid.uuid4()
    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
    finally:
        db.close()

    response = client.get(
        f"/api/ops/compliance-report/{election_id}",
        headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["election_id"] == str(election_id)
    assert "controls" in data
    assert "report_hash" in data


# US-74: Replay Timeline

def test_epic5_replay_timeline():
    election_id = uuid.uuid4()
    db = SessionLocal()
    try:
        _ensure_election(db, election_id)
        db.add(LedgerEvent(
            election_id=election_id,
            event_type="test_event",
            payload_hash=hashlib.sha256(b"payload").hexdigest()
        ))
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/security/replay-timeline?election_id={election_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["election_id"] == str(election_id)
    assert "timeline_hash" in data
