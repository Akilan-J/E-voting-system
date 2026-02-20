"""
Epic 3 Enhancements - Verification Tests (US-40)
Tests config loading, signature generation/verification, block structure validation.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ledger_service import ledger_service
from app.models.ledger_models import LedgerBlock


class TestEpic3Config:
    """Epic 3 US-40: Block validation configuration is loaded correctly."""

    def test_max_block_size_set(self):
        """Verifying max_block_size config is loaded (default 10MB)."""
        assert ledger_service.max_block_size > 0

    def test_max_entries_per_block_set(self):
        """Verifying max_entries_per_block config is loaded (default 10000)."""
        assert ledger_service.max_entries_per_block > 0

    def test_consensus_timeout_set(self):
        """Verifying consensus_timeout config is loaded (default 300s)."""
        assert ledger_service.consensus_timeout > 0


class TestEpic3Signatures:
    """Epic 3: Signature generation and verification for ledger nodes."""

    def test_sign_method_exists(self):
        """Checking _sign method is available on ledger service."""
        assert hasattr(ledger_service, "_sign")

    def test_verify_signature_method_exists(self):
        """Checking _verify_signature method is available on ledger service."""
        assert hasattr(ledger_service, "_verify_signature")

    def test_validate_block_structure_method_exists(self):
        """Checking _validate_block_structure method is available on ledger service."""
        assert hasattr(ledger_service, "_validate_block_structure")

    def test_signature_is_deterministic(self):
        """Signing the same data twice produces the same signature."""
        sig1 = ledger_service._sign("test_data")
        sig2 = ledger_service._sign("test_data")
        assert sig1 == sig2

    def test_signature_is_64_hex(self):
        """Signature output is a 64-char hex string (SHA-256)."""
        sig = ledger_service._sign("test_data")
        assert len(sig) == 64

    def test_valid_signature_passes_verification(self):
        """A correct signature passes verification when validation is enabled."""
        original = ledger_service.enable_signature_validation
        ledger_service.enable_signature_validation = True
        sig = ledger_service._sign("test_data")
        assert ledger_service._verify_signature("test_data", sig, ledger_service.node_id) is True
        ledger_service.enable_signature_validation = original

    def test_wrong_signature_fails_verification(self):
        """An incorrect signature is rejected when validation is enabled."""
        original = ledger_service.enable_signature_validation
        ledger_service.enable_signature_validation = True
        assert ledger_service._verify_signature("test_data", "0" * 64, ledger_service.node_id) is False
        ledger_service.enable_signature_validation = original


class TestEpic3BlockValidation:
    """Epic 3 US-40: Block structure validation catches malformed blocks."""

    def test_valid_block_accepted(self):
        """A block with correct hash lengths and positive height passes validation."""
        db = MagicMock()
        block = LedgerBlock(height=0, prev_hash="a" * 64, merkle_root="b" * 64,
                            block_hash="c" * 64, entry_count=100)
        is_valid, error = ledger_service._validate_block_structure(block, db)
        assert is_valid is True

    def test_negative_height_rejected(self):
        """A block with negative height is rejected (error: invalid_height)."""
        db = MagicMock()
        block = LedgerBlock(height=-1, prev_hash="a" * 64, merkle_root="b" * 64,
                            block_hash="c" * 64, entry_count=100)
        is_valid, error = ledger_service._validate_block_structure(block, db)
        assert is_valid is False
        assert error == "invalid_height"

    def test_short_hash_rejected(self):
        """A block with a short prev_hash is rejected (error: invalid_hash_length)."""
        db = MagicMock()
        block = LedgerBlock(height=1, prev_hash="short", merkle_root="b" * 64,
                            block_hash="c" * 64, entry_count=5)
        is_valid, error = ledger_service._validate_block_structure(block, db)
        assert is_valid is False
        assert error == "invalid_hash_length"

    def test_too_many_entries_rejected(self):
        """A block exceeding max_entries_per_block is rejected (error: too_many_entries)."""
        db = MagicMock()
        block = LedgerBlock(height=1, prev_hash="a" * 64, merkle_root="b" * 64,
                            block_hash="c" * 64, entry_count=20000)
        is_valid, error = ledger_service._validate_block_structure(block, db)
        assert is_valid is False
        assert error == "too_many_entries"
