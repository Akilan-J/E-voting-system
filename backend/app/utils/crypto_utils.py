import hashlib
import json
import base64
from typing import List, Optional
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

class MerkleTree:
    """
    Implements a simple Merkle Tree for inclusion proofs.
    Usage:
        tree = MerkleTree(["hash1", "hash2", "hash3"])
        root = tree.get_root()
        proof = tree.get_proof(0)
    """
    def __init__(self, leaves: List[str]):
        # Ensure even number of leaves by duplicating last if odd
        self.leaves = leaves
        self.tree = []
        self._build_tree()

    def _build_tree(self):
        if not self.leaves:
            self.tree = [[""]]
            return

        current_level = self.leaves
        self.tree = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)
            
            current_level = next_level
            self.tree.append(current_level)

    def get_root(self) -> str:
        if not self.tree:
            return ""
        return self.tree[-1][0]

    def get_proof(self, index: int) -> List[str]:
        """
        Generate Merkle Proof for a leaf at `index`.
        Returns list of sibling hashes.
        """
        if index >= len(self.leaves) or index < 0:
            raise ValueError("Index out of bounds")

        proof = []
        for level in self.tree[:-1]: # Skip root level
            is_right_node = index % 2 == 1
            sibling_index = index - 1 if is_right_node else index + 1
            
            if sibling_index < len(level):
                proof.append(level[sibling_index])
            else:
                # If odd number of nodes, duplication means sibling is self
                proof.append(level[index])
            
            index //= 2
            
        return proof

    @staticmethod
    def verify_proof(leaf: str, proof: List[str], root: str, index: int) -> bool:
        """
        Verify a Merkle Proof.
        """
        current_hash = leaf
        for sibling_hash in proof:
            is_right_node = index % 2 == 1
            if is_right_node:
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
            index //= 2
            
        return current_hash == root


class Signer:
    """
    Handles digital signatures for artifacts using RSA.
    Generates a fresh key pair on instantiation (simulating an HSM).
    """
    def __init__(self):
        # Generate private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()

    def sign_data(self, data: dict) -> str:
        """
        Sign a dictionary payload. Returns Base64 encoded signature.
        """
        payload_bytes = json.dumps(data, sort_keys=True).encode()
        try:
            signature = self.private_key.sign(
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode()
        except Exception as e:
            return str(e)

    def get_public_key_pem(self) -> str:
        """
        Export public key in PEM format.
        """
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode()

# Global Singleton for the application lifespan
signer = Signer()

# --- Blind Signature Support (From Remote) ---

# Global simplified key storage (In reality, use KMS)
# Generating a key pair for the Issuer
# Note: In a real app, this should probably share the same key as the Signer or be distinct.
# For now, we generate a separate key for blind signing to avoid logic conflicts.
bs_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
bs_public_key = bs_private_key.public_key()

def get_issuer_public_key():
    pem = bs_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode('utf-8')

def sign_blinded_message(blinded_message_int: int) -> int:
    """
    Performs RSA signing of a blinded message (integer).
    s' = (m')^d mod n
    """
    priv_numbers = bs_private_key.private_numbers()
    d = priv_numbers.d
    n = priv_numbers.public_numbers.n
    
    signed_int = pow(blinded_message_int, d, n)
    return signed_int

def verify_signature(message_int: int, signature_int: int) -> bool:
    """
    Verifies s^e = m mod n
    """
    pub_numbers = bs_public_key.public_numbers()
    e = pub_numbers.e
    n = pub_numbers.n
    
    calculated_message = pow(signature_int, e, n)
    return calculated_message == message_int
