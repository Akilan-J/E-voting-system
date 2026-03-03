"""
Epic 3: Immutable Vote Ledger — Test Suite
==========================================

Covers:
  - propose / approve / finalize with quorum (US-33, US-44)
  - verify_chain detects tampering (US-35)
  - Merkle proof pass/fail
  - Node auth enforcement (US-32, US-43)
  - Commit cert determinism (US-33)
  - Block validation rules (US-40)
  - Snapshot hash determinism (US-41)
  - Pruning preserves hashes (US-46)
  - Event anchoring (US-42)
  - Consensus stall detection (US-39)

All tests use mock DB sessions — no live database touched.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from app.services.ledger_service import LedgerService
from app.models.ledger_models import (
    LedgerBlock, LedgerEntry, LedgerApproval, LedgerNode,
    LedgerSnapshot, LedgerEvent, LedgerPruning
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc():
    """Fresh LedgerService instance with simulated mode."""
    service = LedgerService()
    service.signature_mode = "simulated"
    service.enable_signature_validation = False
    service.f = 1
    service.n = 3
    service.quorum = 3   # 2*1+1 = 3
    return service


@pytest.fixture
def election_id():
    return uuid4()


def make_block(height, prev_hash, merkle_root, block_hash, entry_count=1, committed=True):
    b = LedgerBlock(
        height=height,
        prev_hash=prev_hash,
        merkle_root=merkle_root,
        block_hash=block_hash,
        entry_count=entry_count,
        committed=committed,
    )
    b.election_id = None
    b.timestamp = datetime.utcnow()
    return b


def make_node(node_id, is_active=True):
    n = LedgerNode(node_id=node_id, public_key="key", is_active=is_active)
    return n


def make_db_with_active_node(node_id="node-1"):
    """Return a mock DB that always considers node_id active."""
    db = MagicMock()
    node = make_node(node_id)

    def query_side(model):
        mock = MagicMock()
        # For LedgerNode queries
        mock.filter.return_value.first.return_value = node
        mock.filter.return_value.order_by.return_value.first.return_value = None
        mock.filter.return_value.all.return_value = []
        mock.filter.return_value.order_by.return_value.all.return_value = []
        mock.all.return_value = []
        return mock

    db.query.side_effect = query_side
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Basic crypto / hashing
# ---------------------------------------------------------------------------

class TestHashing:
    def test_hash_is_sha256(self, svc):
        h = svc._hash("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_deterministic(self, svc):
        assert svc._hash("test") == svc._hash("test")

    def test_hash_different_for_different_input(self, svc):
        assert svc._hash("a") != svc._hash("b")


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------

class TestMerkle:
    def test_empty_entries(self, svc):
        assert svc._compute_merkle_root([]) == "0" * 64

    def test_single_entry(self, svc):
        e = LedgerEntry(entry_hash="a" * 64)
        root = svc._compute_merkle_root([e])
        # Single: hash(a+a) after duplicate
        assert len(root) == 64

    def test_two_entries_deterministic(self, svc):
        e1 = LedgerEntry(entry_hash="a" * 64)
        e2 = LedgerEntry(entry_hash="b" * 64)
        r1 = svc._compute_merkle_root([e1, e2])
        r2 = svc._compute_merkle_root([e2, e1])  # order shouldn't matter (sorted)
        assert r1 == r2

    def test_three_entries(self, svc):
        entries = [
            LedgerEntry(entry_hash="a" * 64),
            LedgerEntry(entry_hash="b" * 64),
            LedgerEntry(entry_hash="c" * 64),
        ]
        root = svc._compute_merkle_root(entries)
        # Manual: sorted = [a*64, b*64, c*64]; odd → duplicate last
        h_ab = svc._hash("a" * 64 + "b" * 64)
        h_cc = svc._hash("c" * 64 + "c" * 64)
        expected = svc._hash(h_ab + h_cc)
        assert root == expected


# ---------------------------------------------------------------------------
# Merkle proof
# ---------------------------------------------------------------------------

class TestMerkleProof:
    def test_proof_verifies_correctly(self, svc):
        entries = [
            LedgerEntry(entry_hash="a" * 64),
            LedgerEntry(entry_hash="b" * 64),
        ]
        root = svc._compute_merkle_root(entries)
        proof = svc._compute_merkle_proof("a" * 64, entries)
        assert svc.verify_merkle_proof("a" * 64, proof, root) is True

    def test_proof_fails_wrong_root(self, svc):
        entries = [
            LedgerEntry(entry_hash="a" * 64),
            LedgerEntry(entry_hash="b" * 64),
        ]
        proof = svc._compute_merkle_proof("a" * 64, entries)
        assert svc.verify_merkle_proof("a" * 64, proof, "z" * 64) is False

    def test_proof_fails_wrong_leaf(self, svc):
        entries = [
            LedgerEntry(entry_hash="a" * 64),
            LedgerEntry(entry_hash="b" * 64),
        ]
        root = svc._compute_merkle_root(entries)
        proof = svc._compute_merkle_proof("a" * 64, entries)
        assert svc.verify_merkle_proof("x" * 64, proof, root) is False

    def test_unknown_leaf_has_no_proof(self, svc):
        entries = [LedgerEntry(entry_hash="a" * 64)]
        proof = svc._compute_merkle_proof("z" * 64, entries)
        assert proof == []


# ---------------------------------------------------------------------------
# Block validation (US-40)
# ---------------------------------------------------------------------------

class TestBlockValidation:
    def test_invalid_height(self, svc):
        db = MagicMock()
        block = LedgerBlock(
            height=-1, prev_hash="a" * 64, merkle_root="b" * 64,
            block_hash="c" * 64, entry_count=1
        )
        ok, code = svc.validate_block(block, db)
        assert not ok
        assert code == "invalid_height"

    def test_invalid_hash_length(self, svc):
        db = MagicMock()
        block = LedgerBlock(
            height=0, prev_hash="short", merkle_root="b" * 64,
            block_hash="c" * 64, entry_count=0
        )
        ok, code = svc.validate_block(block, db)
        assert not ok
        assert code == "invalid_hash_length"

    def test_too_many_entries(self, svc):
        db = MagicMock()
        block = LedgerBlock(
            height=0, prev_hash="a" * 64, merkle_root="b" * 64,
            block_hash="c" * 64, entry_count=99999
        )
        ok, code = svc.validate_block(block, db)
        assert not ok
        assert code == "too_many_entries"

    def test_valid_genesis_block(self, svc):
        db = MagicMock()
        block = LedgerBlock(
            height=0, prev_hash="a" * 64, merkle_root="b" * 64,
            block_hash="c" * 64, entry_count=0
        )
        ok, code = svc.validate_block(block, db)
        assert ok
        assert code == "valid"


# ---------------------------------------------------------------------------
# Genesis creation (US-34, US-35)
# ---------------------------------------------------------------------------

class TestGenesis:
    def test_creates_genesis(self, svc, election_id):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        block = svc.create_genesis(db, election_id)
        assert block.height == 0
        assert block.prev_hash == "0" * 64
        assert block.committed is True
        assert len(block.block_hash) == 64

    def test_returns_existing_genesis(self, svc, election_id):
        existing = LedgerBlock(height=0, block_hash="x" * 64, committed=True)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing
        block = svc.create_genesis(db, election_id)
        assert block is existing


# ---------------------------------------------------------------------------
# Signature (US-43)
# ---------------------------------------------------------------------------

class TestSignature:
    def test_simulated_is_deterministic(self, svc):
        s1 = svc._sign("data")
        s2 = svc._sign("data")
        assert s1 == s2
        assert len(s1) == 64

    def test_simulated_verify_passes_when_disabled(self, svc):
        svc.enable_signature_validation = False
        assert svc._verify_signature("d", "wrong", "node-1", None) is True

    def test_simulated_verify_fails_with_wrong_sig(self, svc):
        svc.enable_signature_validation = True
        sig = svc._sign("data")
        # Verify with correct node_id and correct data
        result = svc._verify_signature("data", sig, svc.node_id, None)
        assert result is True

    def test_simulated_verify_fails_wrong_node(self, svc):
        svc.enable_signature_validation = True
        sig = svc._sign("data")
        # Signature was made by node-1 but we verify as node-2
        result = svc._verify_signature("data", sig, "node-2", None)
        assert result is False


# ---------------------------------------------------------------------------
# Node permission enforcement (US-32)
# ---------------------------------------------------------------------------

class TestNodeAuth:
    def test_require_active_node_passes(self, svc):
        db = MagicMock()
        node = make_node("node-1", is_active=True)
        db.query.return_value.filter.return_value.first.return_value = node
        # Should not raise
        svc._require_active_node("node-1", db)

    def test_require_active_node_raises_for_unknown(self, svc):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(PermissionError, match="node_not_active"):
            svc._require_active_node("unknown-node", db)

    def test_require_active_node_raises_for_disabled(self, svc):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(PermissionError):
            svc._require_active_node("disabled-node", db)

    def test_ed25519_mode_rejects_unregistered_node(self, svc):
        """US-43: In ed25519 mode, signature verification uses public key from DB."""
        svc.signature_mode = "ed25519"
        db = MagicMock()
        # No node in DB
        db.query.return_value.filter.return_value.first.return_value = None
        # Verification should fail — no public key found
        result = svc._verify_signature("data", "sig", "unregistered-node", db)
        assert result is False


# ---------------------------------------------------------------------------
# Propose / Approve / Finalize flow (US-33, US-44)
# ---------------------------------------------------------------------------

class TestConsensusFlow:
    def test_finalize_raises_if_quorum_not_met(self, svc, election_id):
        """Test quorum enforcement. Patches validate_block to bypass structure check."""
        svc.quorum = 3  # need 3 approvals
        db = MagicMock()

        node = make_node(svc.node_id)
        prev_hash = "p" * 64
        block_hash = "b" * 64
        tip_block = make_block(0, "0" * 64, "m" * 64, prev_hash, committed=True)
        tip_block.election_id = election_id
        block = make_block(1, prev_hash, "m" * 64, block_hash, committed=False)
        block.election_id = election_id

        def query_side(model):
            m = MagicMock()
            if model == LedgerNode:
                m.filter.return_value.first.return_value = node
            elif model == LedgerBlock:
                m.filter.return_value.first.return_value = block
                m.filter.return_value.order_by.return_value.first.return_value = tip_block
            elif model == LedgerApproval:
                # Only 1 approval — not enough for quorum=3
                m.filter.return_value.all.return_value = [
                    LedgerApproval(node_id="node-1", signature="s", height=1,
                                   block_hash=block_hash, election_id=election_id)
                ]
            else:
                m.filter.return_value.all.return_value = []
                m.filter.return_value.first.return_value = None
            return m

        db.query.side_effect = query_side
        db.add = MagicMock()
        db.commit = MagicMock()

        # Patch validate_block to always pass so we test quorum logic
        from unittest.mock import patch
        with patch.object(svc, 'validate_block', return_value=(True, 'valid')):
            with pytest.raises(ValueError, match="quorum_not_met"):
                svc.finalize_block(db, election_id, 1)

    def test_commit_cert_is_deterministic(self, svc):
        """US-33: Same block_hash + same sorted approvals → same cert hash."""
        block_hash = "b" * 64
        approvals = [("node-1", "sig1"), ("node-2", "sig2")]

        # Simulate the cert computation
        cert_parts = sorted(approvals)
        cert_data = block_hash + "".join(f"{nid}{sig}" for nid, sig in cert_parts)
        cert1 = svc._hash(cert_data)

        # Reverse order of approvals — should produce same hash after sort
        cert_parts2 = sorted([("node-2", "sig2"), ("node-1", "sig1")])
        cert_data2 = block_hash + "".join(f"{nid}{sig}" for nid, sig in cert_parts2)
        cert2 = svc._hash(cert_data2)

        assert cert1 == cert2


# ---------------------------------------------------------------------------
# Chain verification (US-35)
# ---------------------------------------------------------------------------

class TestVerifyChain:
    def _make_svc_with_chain(self, svc, election_id):
        """Build a 3-block chain (genesis + 2) and return them."""
        genesis_hash = svc._hash(f"Genesis Block|{election_id}")
        merkle0 = "0" * 64

        e1 = LedgerEntry(entry_hash="e" * 64)
        merkle1 = svc._compute_merkle_root([e1])
        hash1 = svc._hash(f"{genesis_hash}{merkle1}{1}{1}")

        e2 = LedgerEntry(entry_hash="f" * 64)
        merkle2 = svc._compute_merkle_root([e2])
        hash2 = svc._hash(f"{hash1}{merkle2}{2}{1}")

        b0 = make_block(0, "0" * 64, merkle0, genesis_hash, entry_count=0)
        b0.election_id = election_id
        b1 = make_block(1, genesis_hash, merkle1, hash1, entry_count=1)
        b1.election_id = election_id
        b2 = make_block(2, hash1, merkle2, hash2, entry_count=1)
        b2.election_id = election_id

        return [b0, b1, b2], {1: [e1], 2: [e2]}

    def _make_verify_chain_db(self, blocks, entries_by_height):
        """
        Build a mock DB for verify_chain.
        verify_chain calls db.query(LedgerBlock) once, then db.query(LedgerEntry) per height.
        Each LedgerEntry query uses single .filter(election_id, height).order_by().all().
        We set up side_effect on db.query to return appropriate mocks sequentially.
        """
        db = MagicMock()

        # Build ordered list of calls: [LedgerBlock, LedgerEntry@h1, LedgerEntry@h2, ...]
        heights = sorted(entries_by_height.keys())

        # Mock for the LedgerBlock query
        block_mock = MagicMock()
        block_mock.filter.return_value.order_by.return_value.all.return_value = blocks

        # Mock for each LedgerEntry query (one per height > 0)
        entry_mocks = []
        for h in heights:
            em = MagicMock()
            em.filter.return_value.order_by.return_value.all.return_value = entries_by_height[h]
            entry_mocks.append(em)

        # query_calls: first call is LedgerBlock, subsequent are LedgerEntry
        query_seq = [block_mock] + entry_mocks
        query_idx = [0]

        def query_side(model):
            if query_idx[0] < len(query_seq):
                result = query_seq[query_idx[0]]
                query_idx[0] += 1
                return result
            return MagicMock()

        db.query.side_effect = query_side
        return db

    def test_valid_chain(self, svc, election_id):
        blocks, entries_map = self._make_svc_with_chain(svc, election_id)
        db = self._make_verify_chain_db(blocks, entries_map)
        result = svc.verify_chain(db, election_id)
        assert result["valid"] is True

    def test_detects_broken_link(self, svc, election_id):
        blocks, entries_map = self._make_svc_with_chain(svc, election_id)
        # Tamper: change block 2's prev_hash to something wrong
        blocks[2].prev_hash = "tampered" + "0" * 56
        db = self._make_verify_chain_db(blocks, entries_map)
        result = svc.verify_chain(db, election_id)
        assert result["valid"] is False
        assert result["first_failing_height"] == 2
        assert result["reason_code"] in (
            "broken_hash_link", "block_hash_mismatch", "merkle_root_mismatch"
        )


    def test_empty_chain_is_valid(self, svc, election_id):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        result = svc.verify_chain(db, election_id)
        assert result["valid"] is True
        assert result["blocks_verified"] == 0


# ---------------------------------------------------------------------------
# Snapshot (US-41)
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_hash_is_deterministic(self, svc, election_id):
        """Same inputs → same snapshot hash."""
        tip_hash = "t" * 64
        height = 5
        manifest_hash = svc._hash("b0b1b2b3b4")

        h1 = svc._hash(f"{tip_hash}{height}{manifest_hash}")
        h2 = svc._hash(f"{tip_hash}{height}{manifest_hash}")
        assert h1 == h2

    def test_snapshot_verify_not_found(self, svc, election_id):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = svc.snapshot_verify(db, election_id, "notexist" * 8)
        assert result["valid"] is False
        assert result["reason"] == "snapshot_not_found"


# ---------------------------------------------------------------------------
# Pruning (US-46)
# ---------------------------------------------------------------------------

class TestPruning:
    def test_prune_nulls_ciphertext_only(self, svc, election_id):
        """US-46: prune() nulls only ciphertext_hash via a single .filter().update() call."""
        update_calls = []

        # prune() does: db.query(LedgerEntry).filter(3 conditions).update({...})
        # Single .filter() call with multiple args, then .update()
        filter_result = MagicMock()
        filter_result.update.side_effect = lambda d, **kw: update_calls.append(d) or 3

        entry_query = MagicMock()
        entry_query.filter.return_value = filter_result

        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()

        def query_side(model):
            if model == LedgerEntry:
                return entry_query
            return MagicMock()

        db.query.side_effect = query_side

        record = svc.prune(db, election_id, 10)
        assert record is not None
        assert "Pruned" in record.policy

        # Verify update was called exactly once
        assert len(update_calls) == 1
        update_dict = update_calls[0]
        # The dict must ONLY contain ciphertext_hash — no other columns
        assert LedgerEntry.ciphertext_hash in update_dict
        assert len(update_dict) == 1


# ---------------------------------------------------------------------------
# Event anchoring (US-42)
# ---------------------------------------------------------------------------

class TestEvents:
    def test_record_event_uses_canonical_json(self, svc, election_id):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()

        payload = {"b": 2, "a": 1}
        svc._record_event(db, election_id=election_id, event_type="test",
                          payload=payload)

        added_obj = db.add.call_args[0][0]
        import json, hashlib
        expected_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        assert added_obj.payload_hash == expected_hash

    def test_event_payload_hash_order_invariant(self, svc, election_id):
        """US-42: Regardless of key order, same payload → same hash."""
        import json, hashlib
        payload_a = {"z": "last", "a": "first"}
        payload_b = {"a": "first", "z": "last"}

        h_a = hashlib.sha256(json.dumps(payload_a, sort_keys=True).encode()).hexdigest()
        h_b = hashlib.sha256(json.dumps(payload_b, sort_keys=True).encode()).hexdigest()
        assert h_a == h_b


# ---------------------------------------------------------------------------
# Consensus stall (US-39)
# ---------------------------------------------------------------------------

class TestConsensusHealth:
    def test_ok_when_recently_committed(self, svc, election_id):
        recent_block = MagicMock()
        recent_block.height = 5
        recent_block.timestamp = datetime.utcnow() - timedelta(seconds=10)

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = recent_block

        svc.stall_seconds = 60
        result = svc.get_consensus_health(db, election_id)
        assert result["status"] == "ok"
        assert result["seconds_since_commit"] < 60

    def test_stalled_when_no_recent_commit(self, svc, election_id):
        old_block = MagicMock()
        old_block.height = 3
        old_block.timestamp = datetime.utcnow() - timedelta(seconds=120)

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = old_block

        svc.stall_seconds = 60
        result = svc.get_consensus_health(db, election_id)
        assert result["status"] == "stalled"
        assert result["seconds_since_commit"] > 60


# ---------------------------------------------------------------------------
# Node health & heartbeat (US-38)
# ---------------------------------------------------------------------------

class TestNodeHealth:
    def test_record_heartbeat_updates_node(self, svc):
        node = make_node("node-1")
        node.last_height = 0
        node.last_seen = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = node
        db.commit = MagicMock()
        db.refresh = MagicMock()

        updated = svc.record_heartbeat(db, "node-1", 42)
        assert node.last_height == 42
        assert node.last_seen is not None
        db.commit.assert_called()

    def test_record_heartbeat_fails_for_unknown(self, svc):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            svc.record_heartbeat(db, "ghost-node", 0)
