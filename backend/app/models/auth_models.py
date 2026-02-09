from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.models.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    # Store hashed identifier from OIDC/SAML or username for local dev
    # For US-1: "Map verified claims to eligibility lookup key (hashed)"
    identity_hash = Column(String(255), unique=True, index=True, nullable=False) 
    role = Column(String(50), default="voter") # voter, admin, trustee, auditor, security_engineer
    # For trustees: how many votes they can verify
    trustee_vote_limit = Column(Integer, nullable=True)
    trustee_votes_verified = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # US-2: MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True) # Should be encrypted in production
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    security_logs = relationship("SecurityLog", back_populates="user")

class SecurityLog(Base):
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    event_type = Column(String(100), nullable=False) # LOGIN, LOGIN_FAIL, MFA_FAIL, etc.
    ip_address = Column(String(45))
    details = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="security_logs")

# US-3: Eligibility (cached/persisted decision)
class EligibilityRecord(Base):
    __tablename__ = "eligibility_records"
    
    id = Column(Integer, primary_key=True, index=True)
    eligibility_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    identity_hash = Column(String(255), index=True, nullable=False)
    election_id = Column(UUID(as_uuid=True), nullable=False) # Link to election UUID
    is_eligible = Column(Boolean, default=False)
    reason_code = Column(String(50))
    checked_at = Column(DateTime, default=datetime.utcnow)
    
class BlindToken(Base):
    """
    US-4. Store only token hash.
    Token format (election_id, expiry, token_id, signature) and store only token hash.
    """
    __tablename__ = "blind_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(255), unique=True, index=True, nullable=False) # Hash of the unblinded token
    status = Column(String(50), default="UNUSED") # UNUSED, USED, REVOKED
    issued_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    expiry = Column(DateTime, nullable=False)
    election_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Revocation support
    revocation_reason = Column(String(255), nullable=True)
    revoked_at = Column(DateTime, nullable=True)

class Citizen(Base):
    """
    Simulated Source of Truth (e.g. Aadhaar Database)
    """
    __tablename__ = "citizens"
    
    id = Column(Integer, primary_key=True, index=True)
    identity_hash = Column(String(255), unique=True, index=True, nullable=False) # Salted hash
    full_name_hashed = Column(String(255))
    is_eligible_voter = Column(Boolean, default=True)
    is_deceased = Column(Boolean, default=False)
    registration_date = Column(DateTime, default=datetime.utcnow)
    # Geo-location / Jurisdiction for eligibility rules
    jurisdiction_code = Column(String(50), nullable=True)

