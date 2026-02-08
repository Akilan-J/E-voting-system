"""
Threshold Cryptography Service for Epic 4

Implements Shamir's Secret Sharing scheme. Instead of one person
holding the private key (single point of failure), we split it
into 5 shares and require any 3 to decrypt.

Why threshold crypto matters:
- No single trustee can access results alone
- If 2 trustees are compromised, votes are still safe
- Even if 2 trustees are unavailable, we can still decrypt

The math: A polynomial of degree (threshold-1) is used. The secret
is the y-intercept. Each trustee gets a point on the curve.
Any 3 points can reconstruct the polynomial and find the secret.

Author: Kapil (Epic 4)
"""

import secrets
import hashlib
import logging
from typing import List, Tuple, Dict
import base64
import json

logger = logging.getLogger(__name__)


class ThresholdCryptoService:
    """
    Manages secret sharing for trustee-based decryption.
    
    We use a 3-of-5 threshold: there are 5 trustees total,
    and any 3 can work together to decrypt the results.
    """
    
    def __init__(self, threshold: int, total_trustees: int):
        # Sanity checks - threshold must make sense
        if threshold > total_trustees:
            raise ValueError("Threshold cannot exceed total trustees")
        if threshold < 1:
            raise ValueError("Threshold must be at least 1")
        
        self.threshold = threshold
        self.total_trustees = total_trustees
        self.prime = self._generate_large_prime()
        
        logger.info(f"Initialized ThresholdCryptoService: {threshold}-of-{total_trustees}")
    
    def split_secret(self, secret: str) -> List[Dict]:
        """
        Split a secret into shares using Shamir's Secret Sharing
        
        Args:
            secret: The secret to split (e.g., private key)
            
        Returns:
            List of share dictionaries for each trustee
        """
        logger.info(f"Splitting secret into {self.total_trustees} shares (threshold: {self.threshold})...")
        
        # Convert secret to integer
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        secret_int = int.from_bytes(hashlib.sha256(secret_bytes).digest(), byteorder='big')
        
        # Generate random coefficients for polynomial
        coefficients = [secret_int] + [
            secrets.randbelow(self.prime) for _ in range(self.threshold - 1)
        ]
        
        # Generate shares by evaluating polynomial at different points
        shares = []
        for i in range(1, self.total_trustees + 1):
            x = i
            y = self._evaluate_polynomial(coefficients, x, self.prime)
            
            share_data = {
                "share_id": i,
                "x": x,
                "y": y,
                "threshold": self.threshold,
                "total_trustees": self.total_trustees
            }
            
            # Serialize and encode
            share_str = base64.b64encode(
                json.dumps(share_data).encode()
            ).decode()
            
            shares.append({
                "share_id": i,
                "share_data": share_str,
                "trustee_index": i
            })
        
        logger.info(f"Secret split successfully into {len(shares)} shares")
        return shares
    
    def reconstruct_secret(self, shares: List[Dict]) -> str:
        """
        Reconstruct secret from shares using Lagrange interpolation
        
        Args:
            shares: List of share dictionaries (at least threshold shares)
            
        Returns:
            Reconstructed secret
        """
        if len(shares) < self.threshold:
            raise ValueError(
                f"Insufficient shares: {len(shares)} < {self.threshold}"
            )
        
        logger.info(f"Reconstructing secret from {len(shares)} shares...")
        
        # Deserialize shares
        points = []
        for share in shares[:self.threshold]:
            share_data = json.loads(
                base64.b64decode(share["share_data"]).decode()
            )
            points.append((share_data["x"], share_data["y"]))
        
        # Lagrange interpolation at x=0 to get secret
        secret_int = self._lagrange_interpolation(points, 0, self.prime)
        
        # Convert back to bytes
        secret_bytes = secret_int.to_bytes(32, byteorder='big')
        secret_hash = base64.b64encode(secret_bytes).decode()
        
        logger.info("Secret reconstructed successfully")
        return secret_hash
    
    def verify_share(self, share: Dict) -> bool:
        """
        Verify that a share is valid
        
        Args:
            share: Share dictionary to verify
            
        Returns:
            True if share is valid, False otherwise
        """
        try:
            share_data = json.loads(
                base64.b64decode(share["share_data"]).decode()
            )
            
            # Check basic structure
            required_fields = ["share_id", "x", "y", "threshold", "total_trustees"]
            if not all(field in share_data for field in required_fields):
                return False
            
            # Check parameters match
            if (share_data["threshold"] != self.threshold or
                share_data["total_trustees"] != self.total_trustees):
                return False
            
            # Check share_id is in valid range
            if not (1 <= share_data["share_id"] <= self.total_trustees):
                return False
            
            logger.debug(f"Share {share_data['share_id']} verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Share verification failed: {e}")
            return False
    
    def generate_key_commitment(self, public_key: str) -> str:
        """
        Generate a commitment to the public key for verification
        
        Args:
            public_key: Public key to commit to
            
        Returns:
            Commitment hash
        """
        commitment = hashlib.sha256(public_key.encode()).hexdigest()
        logger.debug("Generated key commitment")
        return commitment
    
    def verify_commitment(self, public_key: str, commitment: str) -> bool:
        """
        Verify a public key matches its commitment
        
        Args:
            public_key: Public key to verify
            commitment: Expected commitment hash
            
        Returns:
            True if commitment matches, False otherwise
        """
        actual_commitment = self.generate_key_commitment(public_key)
        is_valid = actual_commitment == commitment
        
        logger.debug(f"Commitment verification: {is_valid}")
        return is_valid
    
    # Helper methods
    def _evaluate_polynomial(self, coefficients: List[int], x: int, prime: int) -> int:
        """Evaluate polynomial at point x"""
        result = 0
        for i, coef in enumerate(coefficients):
            result += coef * pow(x, i, prime)
            result %= prime
        return result
    
    def _lagrange_interpolation(self, points: List[Tuple[int, int]], x: int, prime: int) -> int:
        """Lagrange interpolation at point x"""
        result = 0
        
        for i, (xi, yi) in enumerate(points):
            numerator = 1
            denominator = 1
            
            for j, (xj, _) in enumerate(points):
                if i != j:
                    numerator = (numerator * (x - xj)) % prime
                    denominator = (denominator * (xi - xj)) % prime
            
            # Modular multiplicative inverse
            denominator_inv = pow(denominator, prime - 2, prime)
            lagrange_basis = (numerator * denominator_inv) % prime
            
            result = (result + yi * lagrange_basis) % prime
        
        return result
    
    def _generate_large_prime(self) -> int:
        """Generate a large prime number for the field"""
        # For demonstration, using a pre-computed large prime
        # In production, use a proper prime generation library
        return 2**256 - 2**224 + 2**192 + 2**96 - 1  # A 256-bit prime
    
    def get_threshold_info(self) -> Dict:
        """Get threshold configuration information"""
        return {
            "threshold": self.threshold,
            "total_trustees": self.total_trustees,
            "required_for_decryption": self.threshold,
            "max_unavailable": self.total_trustees - self.threshold
        }


# Global instance
threshold_crypto_service = ThresholdCryptoService(
    threshold=3,  # Default: 3-of-5
    total_trustees=5
)
