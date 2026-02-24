"""
Encryption Service for Epic 4: Privacy-Preserving Tallying

Uses Paillier homomorphic encryption to allow vote aggregation
without decrypting individual votes. This is the core crypto module.

How it works:
1. Generate keypair for the election
2. Encrypt each vote as a one-hot vector (e.g., [0, 1, 0] for candidate 2)
3. Aggregate votes by multiplying ciphertexts (homomorphic addition)
4. Decrypt only the final tally, never individual votes

Author: Kapil (Epic 4)
"""

from phe import paillier
import json
import logging
from typing import List, Dict, Tuple, Optional
import pickle
import base64

logger = logging.getLogger(__name__)


class HomomorphicEncryptionService:
    """
    Handles all encryption operations for the voting system.
    
    The Paillier cryptosystem has a special property: you can add
    encrypted numbers together without knowing their values. This
    lets us count votes while keeping each vote secret.
    """
    
    def __init__(self, key_size: int = 2048):
        # Key size affects security. 2048 bits is standard for elections.
        self.key_size = key_size
        self.public_key = None
        self.private_key = None
        logger.info(f"Initialized HomomorphicEncryptionService with key size {key_size}")
    
    def generate_keypair(self) -> Tuple[str, str]:
        """
        Generate a new public/private keypair
        
        Returns:
            Tuple of (public_key, private_key) as base64 encoded strings
        """
        logger.info("Generating new keypair...")
        self.public_key, self.private_key = paillier.generate_paillier_keypair(n_length=self.key_size)
        
        # Serialize keys
        public_key_str = self._serialize_public_key(self.public_key)
        private_key_str = self._serialize_private_key(self.private_key)
        
        logger.info("Keypair generated successfully")
        return public_key_str, private_key_str
    
    def load_public_key(self, public_key_str: str):
        """Load public key from string"""
        self.public_key = self._deserialize_public_key(public_key_str)
        logger.info("Public key loaded")
    
    def load_private_key(self, private_key_str: str):
        """Load private key from string"""
        self.private_key = self._deserialize_private_key(private_key_str)
        # Also set public key from private key (Paillier private key contains public key)
        self.public_key = self.private_key.public_key
        logger.info("Private key loaded")
    
    def encrypt_vote(self, candidate_id: int, num_candidates: int) -> str:
        """
        Encrypt a vote for a specific candidate
        
        Args:
            candidate_id: ID of the candidate (1-based indexing)
            num_candidates: Total number of candidates
            
        Returns:
            Serialized encrypted vote vector
        """
        if not self.public_key:
            raise ValueError("Public key not loaded")
        
        # Create vote vector (one-hot encoding)
        vote_vector = [0] * num_candidates
        vote_vector[candidate_id - 1] = 1
        
        # Encrypt each component
        encrypted_vector = [self.public_key.encrypt(v) for v in vote_vector]
        
        # Serialize
        encrypted_vote_str = self._serialize_encrypted_vector(encrypted_vector)
        
        logger.debug(f"Encrypted vote for candidate {candidate_id}")
        return encrypted_vote_str
    
    def aggregate_votes(self, encrypted_votes: List[str]) -> str:
        """
        Aggregate multiple encrypted votes using homomorphic addition
        
        Args:
            encrypted_votes: List of serialized encrypted votes
            
        Returns:
            Serialized aggregated encrypted tally
        """
        if not encrypted_votes:
            raise ValueError("No votes to aggregate")
        
        logger.info(f"Aggregating {len(encrypted_votes)} encrypted votes...")
        
        # Deserialize first vote
        aggregated_tally = self._deserialize_encrypted_vector(encrypted_votes[0])
        
        # Add remaining votes homomorphically
        for encrypted_vote_str in encrypted_votes[1:]:
            encrypted_vote = self._deserialize_encrypted_vector(encrypted_vote_str)
            
            # Homomorphic addition
            aggregated_tally = [
                aggregated_tally[i] + encrypted_vote[i]
                for i in range(len(aggregated_tally))
            ]
        
        # Serialize result
        aggregated_str = self._serialize_encrypted_vector(aggregated_tally)
        
        logger.info("Vote aggregation completed")
        return aggregated_str
    
    def decrypt_tally(self, aggregated_tally_str: str) -> List[int]:
        """
        Decrypt aggregated tally to get final results
        
        Args:
            aggregated_tally_str: Serialized aggregated encrypted tally
            
        Returns:
            List of vote counts per candidate
        """
        if not self.private_key:
            raise ValueError("Private key not loaded")
        
        logger.info("Decrypting aggregated tally...")
        
        # Deserialize
        encrypted_tally = self._deserialize_encrypted_vector(aggregated_tally_str)
        
        # Decrypt each component
        decrypted_tally = [self.private_key.decrypt(enc_value) for enc_value in encrypted_tally]
        
        logger.info(f"Decryption completed. Results: {decrypted_tally}")
        return decrypted_tally
    
    def partial_decrypt(self, aggregated_tally_str: str, share_index: int) -> str:
        """
        Perform partial decryption for threshold cryptography
        
        Args:
            aggregated_tally_str: Serialized aggregated encrypted tally
            share_index: Index of this trustee's share
            
        Returns:
            Serialized partial decryption
        """
        if not self.private_key:
            raise ValueError("Private key not loaded")
        
        logger.info(f"Performing partial decryption (share {share_index})...")
        
        # For demonstration, we'll simulate partial decryption
        # In production, use proper threshold cryptography library
        encrypted_tally = self._deserialize_encrypted_vector(aggregated_tally_str)
        
        # Simulate partial decryption (simplified)
        partial_result = {
            "share_index": share_index,
            "partial_values": [str(enc.ciphertext()) for enc in encrypted_tally]
        }
        
        partial_str = base64.b64encode(json.dumps(partial_result).encode()).decode()
        
        logger.info("Partial decryption completed")
        return partial_str
    
    def combine_partial_decryptions(
        self,
        aggregated_tally_str: str,
        partial_decryptions: List[str],
        threshold: int
    ) -> List[int]:
        """
        Combine partial decryptions to get final result
        
        Args:
            aggregated_tally_str: Serialized aggregated encrypted tally
            partial_decryptions: List of partial decryptions from trustees
            threshold: Minimum number of trustees required
            
        Returns:
            Final tally results
        """
        if len(partial_decryptions) < threshold:
            raise ValueError(f"Insufficient partial decryptions: {len(partial_decryptions)} < {threshold}")
        
        logger.info(f"Combining {len(partial_decryptions)} partial decryptions (threshold: {threshold})...")
        
        # For demonstration, we'll use full decryption
        # In production, use proper Shamir's Secret Sharing reconstruction
        final_tally = self.decrypt_tally(aggregated_tally_str)
        
        logger.info("Partial decryptions combined successfully")
        return final_tally
    
    # Serialization helpers
    def _serialize_public_key(self, public_key) -> str:
        """Serialize public key to string"""
        key_dict = {
            'n': public_key.n
        }
        return base64.b64encode(json.dumps(key_dict).encode()).decode()
    
    def _serialize_private_key(self, private_key) -> str:
        """Serialize private key to string"""
        key_dict = {
            'p': private_key.p,
            'q': private_key.q
        }
        return base64.b64encode(json.dumps(key_dict).encode()).decode()
    
    def _deserialize_public_key(self, public_key_str: str):
        """Deserialize public key from string"""
        key_dict = json.loads(base64.b64decode(public_key_str).decode())
        return paillier.PaillierPublicKey(n=int(key_dict['n']))
    
    def _deserialize_private_key(self, private_key_str: str):
        """Deserialize private key from string"""
        key_dict = json.loads(base64.b64decode(private_key_str).decode())
        public_key = paillier.PaillierPublicKey(
            n=int(key_dict['p']) * int(key_dict['q'])
        )
        return paillier.PaillierPrivateKey(
            public_key,
            int(key_dict['p']),
            int(key_dict['q'])
        )
    
    def _serialize_encrypted_vector(self, encrypted_vector: List) -> str:
        """Serialize encrypted vector"""
        serialized = []
        for enc_value in encrypted_vector:
            serialized.append({
                'ciphertext': str(enc_value.ciphertext()),
                'exponent': enc_value.exponent
            })
        return base64.b64encode(json.dumps(serialized).encode()).decode()
    
    def _deserialize_encrypted_vector(self, encrypted_vector_str: str) -> List:
        """Deserialize encrypted vector"""
        if not self.public_key:
            raise ValueError("Public key not loaded")
        
        serialized = json.loads(base64.b64decode(encrypted_vector_str).decode())
        encrypted_vector = []
        
        for item in serialized:
            enc_value = paillier.EncryptedNumber(
                self.public_key,
                int(item['ciphertext']),
                int(item['exponent'])
            )
            encrypted_vector.append(enc_value)
        
        return encrypted_vector
    
    def get_public_key_params(self) -> Dict:
        """Get public key parameters for sharing"""
        if not self.public_key:
            raise ValueError("Public key not generated")
        
        return {
            "n": str(self.public_key.n),
            "key_size": self.key_size
        }


import os

# Global instance
key_size = int(os.getenv("KEY_SIZE", 2048))
encryption_service = HomomorphicEncryptionService(key_size=key_size)
