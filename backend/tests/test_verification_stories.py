import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

# US-62: Receipt Verification
def test_receipt_verification():
    # 1. Setup mock election & receipt
    election_id = str(uuid.uuid4())
    receipt_hash = "mock_hash_123"
    
    # 2. Call Verification Endpoint
    response = client.post("/api/verify/receipt", json={
        "receipt_hash": receipt_hash,
        "election_id": election_id
    })
    
    # 3. Assert Response Structure
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "proof" in data
    # Note: Specific logic depends on DB state, but structure must match

# US-63: ZK Proof Verification
def test_zk_proof_verification():
    from app.models.database import SessionLocal, ElectionResult
    import datetime
    
    election_id = str(uuid.uuid4())
    
    # Seed ElectionResult for this test
    db = SessionLocal()
    try:
        from app.models.database import Election
        # 1. Create Parent Election
        db.add(Election(
            election_id=election_id,
            title="Test Election",
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now() + datetime.timedelta(days=1),
            candidates=[],
            status="completed"
        ))
        
        # 2. Create Result
        db.add(ElectionResult(
            election_id=election_id,
            final_tally={"A": 10},
            total_votes_tallied=10,
            verification_hash="hash123",
            published_at=datetime.datetime.now()
        ))
        db.commit()
    finally:
        db.close()

    import hashlib as _hashlib
    merkle_root = "0" * 64  # no ledger entries, so root is all zeros
    proof_bundle = {
        "election_id": election_id,
        "verification_hash": "hash123",
        "ledger_root": merkle_root,
        "proof_hash": _hashlib.sha256(
            f"{election_id}|hash123|{merkle_root}".encode()
        ).hexdigest(),
    }
    
    response = client.post("/api/verify/zk-proof", json={
        "election_id": election_id,
        "proof_bundle": proof_bundle
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True 
    assert "evidence_hash" in data

# US-64: Ledger Replay
def test_ledger_replay():
    election_id = str(uuid.uuid4())
    response = client.post("/api/security/replay-ledger", json={
        "election_id": election_id,
        "verify_signatures": True
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "valid_blocks" in data
    assert "status" in data

# US-65: Transparency Stats (Results Endpoint)
def test_transparency_stats():
    election_id = "00000000-0000-0000-0000-000000000001" # Demo ID
    response = client.get(f"/api/results/{election_id}")
    
    # Might contain "not published" if fresh db, but should return valid JSON
    if response.status_code == 200:
        data = response.json()
        assert "election_id" in data
    else:
        assert response.status_code == 404 # Acceptable if no results yet
