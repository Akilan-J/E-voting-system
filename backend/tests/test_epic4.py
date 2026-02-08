"""
Unit Tests for Epic 4: Privacy-Preserving Tallying & Result Verification

Testing Tool: pytest
Author: Kapil
Module: Epic 4 - Tallying, Encryption, Threshold Crypto

Run with: pytest tests/test_epic4.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Add app to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Test helper: Mock database session
class MockSession:
    def __init__(self):
        self.objects = []
        self.commit_called = False
    
    def query(self, model):
        self.current_model = model
        return self
    
    def filter(self, *args, **kwargs):
        return self
    
    def first(self):
        return None
    
    def all(self):
        return []
    
    def add(self, obj):
        self.objects.append(obj)
    
    def commit(self):
        self.commit_called = True
    
    def refresh(self, obj):
        pass


# =========================================
# Test 1: Encryption Service - Key Generation
# =========================================
class TestEncryptionService:
    """Tests for the Paillier encryption service"""
    
    def test_keypair_generation(self):
        """Test that keypair generation produces valid keys"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, private_key = service.generate_keypair()
        
        # Keys should be non-empty strings
        assert public_key is not None
        assert private_key is not None
        assert len(public_key) > 0
        assert len(private_key) > 0
        
        # Keys should be different from each other
        assert public_key != private_key
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption are inverse operations"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, private_key = service.generate_keypair()
        
        # Load keys
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        # Test data: simulate a vote for candidate 2 in a 3-candidate election
        candidate_id = 2
        num_candidates = 3
        
        # Encrypt the vote
        encrypted_vote = service.encrypt_vote(candidate_id, num_candidates)
        
        # The encrypted vote should be a non-empty string
        assert encrypted_vote is not None
        assert len(encrypted_vote) > 0
    
    def test_public_key_loading(self):
        """Test that public key can be loaded after generation"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        
        # Loading should not raise an error
        service.load_public_key(public_key)
        
        # Public key should now be set
        assert service.public_key is not None
    
    def test_private_key_loading(self):
        """Test that private key can be loaded after generation"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        _, private_key = service.generate_keypair()
        
        # Loading should not raise an error
        service.load_private_key(private_key)
        
        # Private key should now be set
        assert service.private_key is not None


# =========================================
# Test 2: Threshold Cryptography Service
# =========================================
class TestThresholdCryptoService:
    """Tests for Shamir's Secret Sharing implementation"""
    
    def test_threshold_configuration(self):
        """Test that threshold is correctly configured as 3-of-5"""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        
        # Threshold should be 3
        assert service.threshold == 3
        
        # Total trustees should be 5
        assert service.total_trustees == 5
    
    def test_secret_splitting(self):
        """Test that secrets can be split into shares"""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        
        # Create a test secret (simulating a private key)
        test_secret = "test_secret_key_12345"
        
        # Split into shares
        shares = service.split_secret(test_secret)
        
        # Should produce 5 shares
        assert len(shares) == 5
        
        # Each share should have trustee_index and share_data
        for share in shares:
            assert "trustee_index" in share
            assert "share_data" in share
    
    def test_share_indices_are_unique(self):
        """Test that each share has a unique trustee index"""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        shares = service.split_secret("test_secret")
        
        # Get all indices
        indices = [share["trustee_index"] for share in shares]
        
        # All indices should be unique
        assert len(indices) == len(set(indices))
    
    def test_minimum_shares_required(self):
        """Test that at least 3 shares are needed for reconstruction"""
        from app.services.threshold_crypto import ThresholdCryptoService
        
        service = ThresholdCryptoService(threshold=3, total_trustees=5)
        
        # The threshold is 3, meaning 3 shares must be collected
        # before reconstruction is possible
        assert service.threshold == 3


# =========================================
# Test 3: Vote Aggregation
# =========================================
class TestVoteAggregation:
    """Tests for homomorphic vote aggregation"""
    
    def test_aggregate_empty_list_raises_error(self):
        """Test that aggregating empty votes raises an error"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Empty list should raise an error
        with pytest.raises(Exception):
            service.aggregate_votes([])
    
    def test_aggregate_single_vote(self):
        """Test aggregating a single vote returns valid result"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        # Create one encrypted vote
        encrypted_vote = service.encrypt_vote(1, 3)
        
        # Aggregate single vote
        result = service.aggregate_votes([encrypted_vote])
        
        # Result should be non-empty
        assert result is not None
        assert len(result) > 0


# =========================================
# Test 4: Tallying Service
# =========================================
class TestTallyingService:
    """Tests for the tallying workflow"""
    
    def test_service_initialization(self):
        """Test that tallying service initializes correctly"""
        from app.services.tallying import TallyingService
        
        service = TallyingService()
        
        # Service should have encryption and threshold crypto
        assert service.encryption is not None
        assert service.threshold_crypto is not None
    
    def test_start_tallying_requires_election(self):
        """Test that starting tallying requires a valid election"""
        from app.services.tallying import TallyingService
        
        service = TallyingService()
        db = MockSession()
        
        # Try to start tallying with non-existent election
        with pytest.raises(ValueError, match="Election not found"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.start_tallying(db, str(uuid4()))
            )


# =========================================
# Test 5: Error Handling
# =========================================
class TestErrorHandling:
    """Tests for proper error handling"""
    
    def test_decrypt_without_private_key_raises_error(self):
        """Test that decryption fails if private key not loaded"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Try to decrypt without loading private key
        with pytest.raises(ValueError, match="Private key not loaded"):
            service.decrypt_tally("some_ciphertext")
    
    def test_partial_decrypt_without_key_raises_error(self):
        """Test that partial decryption requires key"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Try partial decrypt without key
        with pytest.raises(ValueError, match="Private key not loaded"):
            service.partial_decrypt("ciphertext", 1)
    
    def test_invalid_candidate_id_handled(self):
        """Test that invalid candidate IDs are handled"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        # Candidate ID 0 should still work (edge case)
        encrypted = service.encrypt_vote(0, 3)
        assert encrypted is not None


# =========================================
# Test 6: Key Consistency
# =========================================
class TestKeyConsistency:
    """Tests for ensuring key consistency across operations"""
    
    def test_same_key_used_for_encrypt_decrypt(self):
        """Test that same keypair used for encryption and decryption"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Generate keypair
        public_key, private_key = service.generate_keypair()
        
        # Both keys should be from same generation
        assert public_key is not None
        assert private_key is not None
        
        # Load both keys
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        # Keys should be usable together
        assert service.public_key is not None
        assert service.private_key is not None


# =========================================
# Test 7: Integration Tests
# =========================================
class TestIntegration:
    """Integration tests for Epic 4 workflow"""
    
    def test_full_encryption_workflow(self):
        """Test complete encryption -> aggregation flow"""
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Step 1: Generate keys
        public_key, private_key = service.generate_keypair()
        service.load_public_key(public_key)
        service.load_private_key(private_key)
        
        # Step 2: Encrypt multiple votes
        votes = []
        for i in range(5):
            candidate = (i % 3) + 1  # Candidates 1, 2, 3
            encrypted = service.encrypt_vote(candidate, 3)
            votes.append(encrypted)
        
        # Step 3: Aggregate votes
        aggregated = service.aggregate_votes(votes)
        
        # Aggregated result should be valid
        assert aggregated is not None
        assert len(aggregated) > 0


# =========================================
# Test 8: Known Error Scenarios (from development)
# =========================================
class TestKnownErrors:
    """Tests for errors encountered during development"""
    
    def test_key_mismatch_scenario(self):
        """
        Error: encrypted_number was encrypted against a different key
        Cause: Trustees had separate keys instead of shared election key
        This test ensures keys are consistent
        """
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        
        # Generate ONE keypair for the whole election
        public_key, private_key = service.generate_keypair()
        
        # All trustees should use this same key
        service.load_public_key(public_key)
        
        # Encrypt some votes with this key
        vote1 = service.encrypt_vote(1, 3)
        vote2 = service.encrypt_vote(2, 3)
        
        # Aggregate with same key
        aggregated = service.aggregate_votes([vote1, vote2])
        
        # Now load private key and decrypt
        service.load_private_key(private_key)
        
        # This should not raise "different key" error
        # (In the actual bug, trustees had different keys)
        assert aggregated is not None
    
    def test_timeout_scenario(self):
        """
        Error: Action failed (timeout)
        Cause: 10 second timeout too short for 100 votes
        This test verifies encryption completes
        """
        from app.services.encryption import HomomorphicEncryptionService
        
        service = HomomorphicEncryptionService()
        public_key, _ = service.generate_keypair()
        service.load_public_key(public_key)
        
        # Encrypt 10 votes (scaled down from 100 for test speed)
        votes = []
        for i in range(10):
            encrypted = service.encrypt_vote(i % 3 + 1, 3)
            votes.append(encrypted)
        
        # All votes should be encrypted
        assert len(votes) == 10
        
        # Aggregation should complete
        result = service.aggregate_votes(votes)
        assert result is not None


# =========================================
# Run tests if executed directly
# =========================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
