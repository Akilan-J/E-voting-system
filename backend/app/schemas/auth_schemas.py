from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    identity_hash: str
    role: str = "voter"

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

class EligibilityResponse(BaseModel):
    is_eligible: bool
    reason_code: Optional[str] = None
    election_id: UUID

class BlindSignRequest(BaseModel):
    election_id: UUID
    blinded_payload: str

class BlindSignResponse(BaseModel):
    signature: str

