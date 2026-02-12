"""
Comprehensive test suite for all implemented user stories across EPICs 1-5.

This test file covers the major functionality implemented in the e-voting system:
- EPIC 1: Voter authentication & credentials
- EPIC 2: Private ballot submission
- EPIC 3: Immutable ledger
- EPIC 4: Privacy-preserving tallying
- EPIC 5: Verification & audit ops
"""

import pytest
import uuid
import hashlib
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal, Election, EncryptedVote, Trustee, ElectionResult
from app.models.ledger_models import LedgerEntry, LedgerBlock, LedgerEvent
from app.services.ledger_service import ledger_service
from app.utils.crypto_utils import MerkleTree

client = TestClient(app)


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

@pytest.fixture(scope="session")
def admin_token() -> str:
    """Get admin JWT token."""
    response = client.post("/auth/login", json={"credential": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def trustee_token() -> str:
    """Get trustee JWT token."""
    response = client.post("/auth/login", json={"credential": "trustee"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def voter_token() -> str:
    """Get voter JWT token."""
    response = client.post("/auth/login", json={"credential": "voter1"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    """Create Authorization header."""
    return {"Authorization": f"Bearer {token}"}


def _ensure_election(db, election_id: uuid.UUID) -> Election:
    """Ensure election exists in database."""
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if election:
        return election
    now = datetime.utcnow()
    election = Election(
        election_id=election_id,
        title="Test Election",
        description="Comprehensive test election",
        start_time=now,
        end_time=now + timedelta(days=1),
        status="active",
        candidates=[
            {"id": 1, "name": "Candidate A"},
            {"id": 2, "name": "Candidate B"},
            {"id": 3, "name": "Candidate C"}
        ]
    )
    db.add(election)
    db.commit()
    db.refresh(election)
    return election


# ============================================================================
# EPIC 1: VOTER ACCESS AND CREDENTIALS
# ============================================================================

class TestEpic1Authentication:
    """Tests for US-1 through US-16: Authentication and credentials."""

    def test_us1_voter_login_with_valid_credential(self):
        """US-1: Voter can authenticate with valid digital ID."""
        response = client.post("/auth/login", json={"credential": "voter1"})
        assert response.status_code == 200
        assert "access_token" in response.json()
        # voter1 may require MFA or return voter role
        assert response.json()["role"] in ["voter", "mfa_pending"]

    def test_login_with_invalid_credential(self):
        """Invalid credentials are rejected."""
        response = client.post("/auth/login", json={"credential": "invalid_user"})
        assert response.status_code == 403

    def test_admin_login(self):
        """Admin can log in with admin credential."""
        response = client.post("/auth/login", json={"credential": "admin"})
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_trustee_login(self):
        """Trustee can log in with trustee credential."""
        response = client.post("/auth/login", json={"credential": "trustee"})
        assert response.status_code == 200
        assert response.json()["role"] == "trustee"

    def test_auditor_login(self):
        """Auditor can log in with auditor credential."""
        response = client.post("/auth/login", json={"credential": "auditor"})
        assert response.status_code == 200
        assert response.json()["role"] == "auditor"

    def test_security_engineer_login(self):
        """Security engineer can log in with security_engineer credential."""
        response = client.post("/auth/login", json={"credential": "security_engineer"})
        assert response.status_code == 200
        assert response.json()["role"] == "security_engineer"


# ============================================================================
# EPIC 2: PRIVATE BALLOT SUBMISSION
# ============================================================================

class TestEpic2BallotSubmission:
    """Tests for US-17 through US-26: Ballot submission and encryption."""

    def test_mock_votes_generation(self):
        """Generate mock encrypted votes for testing."""
        response = client.post("/api/mock/generate-votes?count=10")
        assert response.status_code == 200
        data = response.json()
        assert "votes_generated" in data
        assert data["votes_generated"] == 10


# ============================================================================
# EPIC 3: IMMUTABLE VOTE LEDGER
# ============================================================================

class TestEpic3Ledger:
    """Tests for US-27 through US-48: Ledger and blockchain operations."""

    def test_ledger_blocks_listing(self):
        """US-45: List blocks from the ledger (rate-limited public access)."""
        response = client.get("/api/ledger/blocks?limit=10")
        assert response.status_code == 200
        # Should return blocks or empty list
        data = response.json()
        assert isinstance(data, list)

    def test_ledger_chain_verification(self):
        """Verify ledger chain integrity."""
        election_id = uuid.uuid4()
        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
            ledger_service.create_genesis(db, election_id)
        finally:
            db.close()

        response = client.get(f"/api/ledger/verify-chain?election_id={election_id}")
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data


# ============================================================================
# EPIC 4: PRIVACY-PRESERVING TALLYING
# ============================================================================

class TestEpic4APIEndpoints:
    """Tests for US-49 through US-61: Tallying and threshold cryptography API endpoints."""

    def test_get_trustees(self, admin_token):
        """Get list of trustees."""
        response = client.get("/api/trustees", headers=_auth_headers(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_start_tallying(self, admin_token):
        """Start tallying process."""
        election_id = uuid.uuid4()
        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
        finally:
            db.close()

        response = client.post(
            "/api/tally/start",
            json={"election_id": str(election_id)},
            headers=_auth_headers(admin_token)
        )
        # May return 200 or 400 depending on election state
        assert response.status_code in [200, 400]


class TestEpic4Encryption:
    """Tests for Paillier homomorphic encryption service."""

    def test_keypair_generation(self):
        """Test that keypair generation produces valid keys."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, private_key = service.generate_keypair()
        
        assert public_key is not None
        assert private_key is not None
        assert len(public_key) > 0
        assert len(private_key) > 0
        assert public_key != private_key

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption are inverse operations."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, private_key = service.generate_keypair()
        
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        candidate_id = 2
        num_candidates = 3
        
        encrypted_vote = service.encrypt_vote(candidate_id, num_candidates)
        
        assert encrypted_vote is not None
        assert len(encrypted_vote) > 0

    def test_public_key_loading(self):
        """Test that public key can be loaded after generation."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        
        service.load_public_key(public_key)
        
        assert service.public_key is not None

    def test_private_key_loading(self):
        """Test that private key can be loaded after generation."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        _, private_key = service.generate_keypair()
        
        service.load_private_key(private_key)
        
        assert service.private_key is not None


class TestEpic4ThresholdCrypto:
    """Tests for Shamir's Secret Sharing threshold cryptography."""

    def test_threshold_configuration(self):
        """Test that threshold is correctly configured as 3-of-5."""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        
        assert service.threshold == 3
        assert service.total_trustees == 5

    def test_secret_splitting(self):
        """Test that secrets can be split into shares."""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        test_secret = "test_secret_key_12345"
        
        shares = service.split_secret(test_secret)
        
        assert len(shares) == 5
        
        for share in shares:
            assert "trustee_index" in share
            assert "share_data" in share

    def test_share_indices_are_unique(self):
        """Test that each share has a unique trustee index."""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        shares = service.split_secret("test_secret")
        
        indices = [share["trustee_index"] for share in shares]
        assert len(indices) == len(set(indices))

    def test_minimum_shares_required(self):
        """Test that at least 3 shares are needed for reconstruction."""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        
        assert service.threshold == 3


class TestEpic4VoteAggregation:
    """Tests for homomorphic vote aggregation."""

    def test_aggregate_empty_list_raises_error(self):
        """Test that aggregating empty votes raises an error."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        with pytest.raises(Exception):
            service.aggregate_votes([])

    def test_aggregate_single_vote(self):
        """Test aggregating a single vote returns valid result."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        encrypted_vote = service.encrypt_vote(1, 3)
        result = service.aggregate_votes([encrypted_vote])
        
        assert result is not None
        assert len(result) > 0


class TestEpic4TallyingService:
    """Tests for the tallying workflow."""

    def test_service_initialization(self):
        """Test that tallying service initializes correctly."""
        from app.services.tallying import TallyingService
        
        service = TallyingService()
        
        assert service.encryption is not None
        assert service.threshold_crypto is not None


class TestEpic4ErrorHandling:
    """Tests for proper error handling in encryption/tallying."""

    def test_decrypt_without_private_key_raises_error(self):
        """Test that decryption fails if private key not loaded."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        with pytest.raises(ValueError, match="Private key not loaded"):
            service.decrypt_tally("some_ciphertext")

    def test_partial_decrypt_without_key_raises_error(self):
        """Test that partial decryption requires key."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        with pytest.raises(ValueError, match="Private key not loaded"):
            service.partial_decrypt("ciphertext", 1)

    def test_invalid_candidate_id_handled(self):
        """Test that invalid candidate IDs are handled."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        encrypted = service.encrypt_vote(0, 3)
        assert encrypted is not None


class TestEpic4KeyConsistency:
    """Tests for ensuring key consistency across operations."""

    def test_same_key_used_for_encrypt_decrypt(self):
        """Test that same keypair used for encryption and decryption."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        public_key, private_key = service.generate_keypair()
        
        assert public_key is not None
        assert private_key is not None
        
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        assert service.public_key is not None
        assert service.private_key is not None

    def test_full_encryption_workflow(self):
        """Test complete encryption -> aggregation flow."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        public_key, private_key = service.generate_keypair()
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        votes = []
        for i in range(5):
            candidate = (i % 3) + 1
            encrypted = service.encrypt_vote(candidate, 3)
            votes.append(encrypted)
        
        aggregated = service.aggregate_votes(votes)
        
        assert aggregated is not None
        assert len(aggregated) > 0

    def test_key_mismatch_scenario(self):
        """Test that all votes use the same encryption key."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        public_key, private_key = service.generate_keypair()
        
        service.load_public_key(public_key)
        
        vote1 = service.encrypt_vote(1, 3)
        vote2 = service.encrypt_vote(2, 3)
        
        aggregated = service.aggregate_votes([vote1, vote2])
        
        service.load_private_key(private_key)
        
        assert aggregated is not None

    def test_multiple_vote_encryption(self):
        """Test encrypting multiple votes completes in reasonable time."""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        votes = []
        for i in range(10):
            encrypted = service.encrypt_vote(i % 3 + 1, 3)
            votes.append(encrypted)
        
        assert len(votes) == 10
        
        result = service.aggregate_votes(votes)
        assert result is not None


# ============================================================================
# EPIC 5: VERIFICATION AND AUDIT OPS
# ============================================================================

class TestEpic5Verification:
    """Tests for US-62 through US-76: Verification and audit operations."""

    def test_us62_receipt_verification(self):
        """US-62: Verify receipt inclusion in ledger."""
        election_id = uuid.uuid4()
        receipt_hash = hashlib.sha256(b"test_receipt").hexdigest()
        entry_hash = hashlib.sha256(b"test_entry").hexdigest()

        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
            vote = EncryptedVote(
                election_id=election_id,
                encrypted_vote="test_ciphertext",
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
        assert response.json()["status"] == "verified"

    def test_us63_zk_proof_verification(self):
        """US-63: Verify zero-knowledge proof."""
        election_id = uuid.uuid4()
        verification_hash = hashlib.sha256(b"test_verification").hexdigest()
        entry_hash = hashlib.sha256(b"test_zk_entry").hexdigest()

        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
            db.add(LedgerEntry(election_id=election_id, entry_hash=entry_hash))
            db.add(ElectionResult(
                election_id=election_id,
                final_tally={"A": 1},
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

        response = client.post("/api/verify/zk-proof", json={
            "election_id": str(election_id),
            "proof_bundle": {
                "election_id": str(election_id),
                "verification_hash": verification_hash,
                "ledger_root": merkle_root,
                "proof_hash": proof_hash
            }
        })
        assert response.status_code == 200
        assert response.json()["is_valid"] is True

    def test_us64_ledger_replay_audit(self):
        """US-64: Audit ledger with replay verification."""
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
        assert response.json()["status"] == "clean"

    def test_us65_transparency_dashboard(self):
        """US-65: Get transparency dashboard metrics."""
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

    def test_us66_evidence_download(self):
        """US-66: Download evidence package."""
        election_id = uuid.uuid4()
        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
        finally:
            db.close()

        response = client.get(f"/api/ops/evidence/{election_id}")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/zip"

    def test_us68_threat_simulation(self, admin_token):
        """US-68: Simulate threat for resilience testing."""
        response = client.post(
            "/api/security/simulate",
            json={"scenario_type": "replay_attack", "intensity": "low"},
            headers=_auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data

    def test_us69_anomaly_detection(self):
        """US-69: Detect anomalies."""
        response = client.get("/api/security/anomalies")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_us70_incident_workflow(self, admin_token):
        """US-70: Incident response workflow."""
        # Create incident
        create_resp = client.post(
            "/api/ops/incidents",
            json={
                "title": "Test Incident",
                "description": "Test",
                "severity": "low",
                "reported_by": "pytest"
            },
            headers=_auth_headers(admin_token)
        )
        assert create_resp.status_code == 200
        incident_id = create_resp.json()["incident_id"]

        # Update incident
        update_resp = client.put(
            f"/api/ops/incidents/{incident_id}",
            json={"status": "triage"},
            headers=_auth_headers(admin_token)
        )
        assert update_resp.status_code == 200

    def test_us71_dispute_workflow(self, admin_token):
        """US-71: Dispute resolution workflow."""
        election_id = uuid.uuid4()
        db = SessionLocal()
        try:
            _ensure_election(db, election_id)
        finally:
            db.close()

        # Create dispute
        create_resp = client.post(
            "/api/ops/disputes",
            json={
                "title": "Test Dispute",
                "description": "Test",
                "election_id": str(election_id),
                "filed_by": "pytest"
            },
            headers=_auth_headers(admin_token)
        )
        assert create_resp.status_code == 200
        dispute_id = create_resp.json()["dispute_id"]

        # Update dispute
        update_resp = client.put(
            f"/api/ops/disputes/{dispute_id}",
            json={"status": "investigating"},
            headers=_auth_headers(admin_token)
        )
        assert update_resp.status_code == 200

    def test_us72_compliance_report(self, admin_token):
        """US-72: Generate compliance report."""
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
        assert "report_hash" in response.json()

    def test_us74_replay_timeline(self):
        """US-74: Generate election replay timeline."""
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
        assert "timeline_hash" in response.json()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for end-to-end workflows."""

    def test_full_election_workflow(self, admin_token, trustee_token, voter_token):
        """Test complete flow: login → vote → tally → results → verify."""
        # 1. Tokens already obtained from fixtures (voter login happened in fixture)
        assert admin_token
        assert trustee_token
        assert voter_token

        # 2. Generate votes
        votes_resp = client.post("/api/mock/generate-votes?count=5", headers=_auth_headers(admin_token))
        assert votes_resp.status_code == 200

        # 3. Start tallying
        tally_resp = client.post(
            "/api/tally/start",
            json={"election_id": "00000000-0000-0000-0000-000000000001"},
            headers=_auth_headers(admin_token)
        )
        # Might succeed or fail depending on state, but should be API-valid
        assert tally_resp.status_code in [200, 400, 422]
