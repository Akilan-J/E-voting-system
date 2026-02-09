from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    identity_hash: str
    role: str = "voter"  # voter, admin, trustee, auditor, security_engineer
    trustee_vote_limit: Optional[int] = None
    trustee_votes_verified: Optional[int] = 0

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    user_id: UUID
    is_active: bool
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    mfa_required: bool = False

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    role: Optional[str] = None

class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str

class MFAVerifyRequest(BaseModel):
    token: str

class LoginRequest(BaseModel):
    # For US-1, we simulate OIDC by accepting a "credential" or "id_token"
    # In a real OIDC flow, this would be an authorization code or ID token.
    # For now, we'll accept a mock identity string to hash.
    credential: str
    password: Optional[str] = None # Or proof

class RoleUpdateRequest(BaseModel):
    role: str
    trustee_vote_limit: Optional[int] = None

class EligibilityResponse(BaseModel):
    is_eligible: bool
    reason_code: Optional[str] = None
    election_id: UUID

class BlindSignRequest(BaseModel):
    election_id: UUID
    blinded_payload: str

class BlindSignResponse(BaseModel):
    signature: str

class VoteCastRequest(BaseModel):
    election_id: UUID
    token: str # Unblinded token (integer string)
    signature: str # Signature from server (integer string)
    vote_ciphertext: str
    nonce: str
    vote_proof: Optional[str] = None
    client_integrity: Optional[str] = None
    version: Optional[str] = "v1"
    
class VoteCastResponse(BaseModel):
    status: str
    receipt_hash: str
    timestamp: datetime

class CredentialRevokeRequest(BaseModel):
    election_id: UUID
    token_hash: str
    reason: Optional[str] = None

class VoterRegistrationRequest(BaseModel):
    credential: str
    is_eligible_voter: bool = True
    jurisdiction_code: Optional[str] = None

