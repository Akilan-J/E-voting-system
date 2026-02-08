import os
import time
import hashlib
import json
import enum
import secrets
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from app.models.database import AuditLog, Trustee
from app.models.auth_models import User, BlindToken

# --- Constants & Risk Scoring ---
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
TOKEN_EXPIRY_HOURS = 24

class SecurityEvent(enum.Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAIL = "LOGIN_FAIL"
    MFA_FAIL = "MFA_FAIL"
    CREDENTIAL_ISSUED = "CREDENTIAL_ISSUED"
    VOTE_CAST = "VOTE_CAST"
    ADMIN_ACTION = "ADMIN_ACTION"
    KEY_ROTATION = "KEY_ROTATION"

class RiskLevel(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecurityRiskAnalyzer:
    """
    Privacy-preserving risk scoring based on access patterns.
    Does not store raw PII for analysis, uses hashed constructs or aggregate counters.
    """
    @staticmethod
    def calculate_risk(ip_address: str, user_id: str, db: Session) -> RiskLevel:
        # 1. IP Velocity Check (Reddis or DB based count)
        # Simplified: Check last 5 failed logins for this IP
        recent_fails = db.query(AuditLog).filter(
            AuditLog.ip_address == ip_address,
            AuditLog.status == "FAILURE",
            AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=10)
        ).count()
        
        if recent_fails > 10:
            return RiskLevel.CRITICAL
        if recent_fails > 5:
            return RiskLevel.HIGH
            
        # 2. Geo-match (Placeholder logic)
        # In prod: Compare IP geo with user jurisdiction
        
        return RiskLevel.LOW

# --- Immutable Audit Logging ---
class ImmutableLogger:
    @staticmethod
    def log(
        db: Session, 
        election_id: Optional[str], 
        operation: str, 
        actor: str, 
        details: Dict[str, Any], 
        status: str, 
        ip: str
    ):
        """
        Creates a hash-chained audit log entry.
        """
        # 1. Get last log hash
        last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = last_log.current_hash if last_log else "0" * 64
        
        # 2. Construct entry
        current_time = datetime.utcnow()
        entry_string = f"{prev_hash}{election_id}{operation}{actor}{json.dumps(details, sort_keys=True)}{status}{current_time.isoformat()}{ip}"
        current_hash = hashlib.sha256(entry_string.encode()).hexdigest()
        
        log_entry = AuditLog(
            election_id=election_id,
            operation_type=operation,
            performed_by=actor,
            details=details,
            status=status,
            timestamp=current_time,
            ip_address=ip,
            previous_hash=prev_hash,
            current_hash=current_hash
        )
        db.add(log_entry)
        # db.commit() # Caller commits transaction

# --- Key Management & HSM Simulation ---
class KeyManager:
    """
    Simulated HSM / KMS Integration.
    Strict prohibition of plaintext private keys export.
    """
    
    _instance = None
    _rsa_private_key = None # Loaded only in memory, never logged
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = KeyManager()
        return cls._instance
    
    def __init__(self):
        self._load_keys()
        
    def _load_keys(self):
        """
        Load keys from secure 'storage' (simulated by non-committed path or env var).
        In PROD: Use AWS KMS / CloudHSM APIs.
        """
        # For demo, generate if not exists in memory (simulated secure boot)
        if not self._rsa_private_key:
            self._rsa_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
    def get_public_key_pem(self) -> str:
        public_key = self._rsa_private_key.public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
    def get_rsa_components(self) -> Tuple[int, int]:
        """Returns (n, d) for blind signing. 
        CRITICAL: Only for internal crypto operations, never exposed API."""
        priv_numbers = self._rsa_private_key.private_numbers()
        return priv_numbers.public_numbers.n, priv_numbers.d

    def sign_data(self, data: bytes) -> bytes:
        """Standard signing using KMS key"""
        return self._rsa_private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

# --- Blind Signatures ---
class BlindSigner:
    """
    Implements RSA Blind Signatures.
    Server side logic: Sign a blinded message.
    """
    @staticmethod
    def sign_blinded_int(blinded_int: int) -> int:
        """
        s' = (m')^d mod n
        """
        km = KeyManager.get_instance()
        n, d = km.get_rsa_components()
        
        # Verify range
        if not (0 < blinded_int < n):
            raise ValueError("Blinded message out of range")
            
        return pow(blinded_int, d, n)

    @staticmethod
    def verify_token_signature(token_int: int, signature_int: int) -> bool:
        """
        Verifies s^e = m mod n
        Used to verify the unblinded token presented by the voter.
        """
        km = KeyManager.get_instance()
        # For verification we technically only need public key, but here we use the loaded key manager
        # Get public components
        pub_key_pem = km.get_public_key_pem()
        # Parse PEM to get numbers (inefficient but safe)
        from cryptography.hazmat.primitives.asymmetric import rsa
        pub_key = serialization.load_pem_public_key(
            pub_key_pem.encode(), 
            backend=default_backend()
        )
        pub_numbers = pub_key.public_numbers()
        e = pub_numbers.e
        n = pub_numbers.n
        
        calculated_msg = pow(signature_int, e, n)
        return calculated_msg == token_int

# --- Role Based Access Control ---
class RBAC:
    """
    Enforces Role-Based Access Control.
    """
    ROLES_PERMISSIONS = {
        "voter": ["vote:cast", "credential:issue", "results:view"],
        "trustee": ["key:generate", "tally:decrypt", "results:view"],
        "auditor": ["logs:view", "results:audit", "results:view"],
        "admin": ["users:manage", "election:manage"]
    }
    
    @staticmethod
    def check_permission(user_role: str, required_permission: str):
        if user_role not in RBAC.ROLES_PERMISSIONS:
            raise HTTPException(status_code=403, detail="Role not recognized")
            
        if required_permission not in RBAC.ROLES_PERMISSIONS[user_role]:
             raise HTTPException(status_code=403, detail=f"Permission {required_permission} denied for role {user_role}")

# --- Threshold Crypto Simulation ---
class ThresholdCrypto:
    """
    Simulated t-of-n Shamir Secret Sharing management.
    Real implementation would use 'ssl' library appropriately.
    """
    @staticmethod
    def distribute_shares(secret: int, t: int, n: int) -> List[Tuple[int, int]]:
        """
        Generates shares (x, y) for secret.
        Simple polynomial implementation for demo.
        """
        coefs = [secret] + [secrets.randbelow(10**50) for _ in range(t-1)]
        shares = []
        for i in range(1, n+1):
            x = i
            # Evaluate polynomial at x
            y = sum(c * (x**exp) for exp, c in enumerate(coefs))
            shares.append((x, y))
        return shares
