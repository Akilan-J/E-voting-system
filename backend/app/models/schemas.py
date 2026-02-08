"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Trustee Schemas
class TrusteeBase(BaseModel):
    name: str
    email: EmailStr


class TrusteeCreate(TrusteeBase):
    pass


class TrusteeResponse(TrusteeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    trustee_id: UUID
    status: str
    created_at: datetime
    has_key_share: bool = False


# Election Schemas
class CandidateSchema(BaseModel):
    id: int
    name: str
    party: str


class ElectionBase(BaseModel):
    title: str
    description: Optional[str] = None
    candidates: List[CandidateSchema]


class ElectionResponse(ElectionBase):
    model_config = ConfigDict(from_attributes=True)
    
    election_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    total_voters: int
    created_at: datetime


# Encrypted Vote Schemas
class EncryptedVoteCreate(BaseModel):
    election_id: UUID
    encrypted_vote: str
    vote_proof: Optional[str] = None
    nonce: str


class EncryptedVoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    vote_id: UUID
    election_id: UUID
    timestamp: datetime
    is_tallied: bool


# Tallying Schemas
class TallyStartRequest(BaseModel):
    election_id: UUID


class TallyStartResponse(BaseModel):
    session_id: UUID
    election_id: UUID
    status: str
    message: str
    total_votes: int
    required_trustees: int


class PartialDecryptRequest(BaseModel):
    election_id: UUID
    trustee_id: UUID


class PartialDecryptResponse(BaseModel):
    decryption_id: UUID
    election_id: UUID
    trustee_id: UUID
    status: str
    message: str
    timestamp: datetime


class TallyFinalizeRequest(BaseModel):
    election_id: UUID


class TallyFinalizeResponse(BaseModel):
    result_id: UUID
    election_id: UUID
    final_tally: Dict[str, int]
    total_votes_tallied: int
    verification_hash: str
    message: str


class TallyStatusResponse(BaseModel):
    session_id: UUID
    election_id: UUID
    status: str
    required_trustees: int
    completed_trustees: int
    started_at: datetime
    completed_at: Optional[datetime] = None


# Result Schemas
class ElectionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    result_id: UUID
    election_id: UUID
    final_tally: Dict[str, int]
    total_votes_tallied: int
    verification_hash: str
    is_verified: bool
    published_at: Optional[datetime] = None
    blockchain_tx_hash: Optional[str] = None


class ResultVerificationRequest(BaseModel):
    election_id: UUID


class ResultVerificationResponse(BaseModel):
    election_id: UUID
    is_valid: bool
    verification_hash: str
    verification_details: Dict[str, Any]
    timestamp: datetime


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    log_id: UUID
    operation_type: str
    performed_by: Optional[str]
    details: Optional[Dict[str, Any]]
    status: str
    timestamp: datetime


# Mock Data Schemas
class MockVotesGenerateRequest(BaseModel):
    election_id: Optional[UUID] = None
    count: int = Field(default=100, ge=1, le=10000)
    candidate_distribution: Optional[Dict[int, float]] = None


class MockVotesGenerateResponse(BaseModel):
    message: str
    election_id: UUID
    votes_generated: int
    distribution: Dict[str, int]


# Key Generation Schemas
class KeyShareGenerateRequest(BaseModel):
    trustee_id: UUID
    election_id: UUID


class KeyShareGenerateResponse(BaseModel):
    trustee_id: UUID
    public_key: str
    message: str


# Generic Response Schemas
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
# Anonymous Voting Schemas

from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class EligibilityResponse(BaseModel):
    is_eligible: bool
    reason_code: Optional[str] = None
    election_id: UUID


class BlindSignRequest(BaseModel):
    election_id: UUID
    blinded_payload: str


class BlindSignResponse(BaseModel):
    signature: str


class CastVoteRequest(BaseModel):
    election_id: UUID
    encrypted_vote: str
    token: str
    signature: str
