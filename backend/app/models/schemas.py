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

# Incident Schemas (US-70)
class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str
    reported_by: Optional[str] = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    incident_id: UUID
    title: str
    description: str
    severity: str
    status: str
    reported_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolution_notes: Optional[str] = None



class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None


class IncidentActionCreate(BaseModel):
    action_type: str
    details: Optional[Dict[str, Any]] = None


class IncidentActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: UUID
    incident_id: Optional[UUID] = None
    dispute_id: Optional[UUID] = None
    actor: Optional[str] = None
    action_type: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class DisputeCreate(BaseModel):
    title: str
    description: str
    evidence: Optional[List[str]] = None
    election_id: Optional[UUID] = None
    filed_by: Optional[str] = None


class DisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dispute_id: UUID
    election_id: Optional[UUID] = None
    title: str
    description: str
    status: str
    filed_by: Optional[str] = None
    evidence: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    resolution_notes: Optional[str] = None


class DisputeUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    evidence: Optional[List[str]] = None


# US-62: Receipt Verification Schemas
class ReceiptVerificationRequest(BaseModel):
    receipt_hash: str
    election_id: UUID


class ReceiptVerificationResponse(BaseModel):
    receipt_hash: str
    status: str  # verified, not_found, invalid
    block_index: Optional[int] = None
    timestamp: Optional[datetime] = None
    proof: Optional[Dict[str, Any]] = None


# US-63: ZK Proof Verification Schemas
class ZKProofVerificationRequest(BaseModel):
    election_id: UUID
    proof_bundle: Dict[str, Any]


class ZKProofVerificationResponse(BaseModel):
    is_valid: bool
    verification_time_ms: float
    evidence_hash: str
    details: Dict[str, Any]


# US-68: Threat Simulation Schemas
class ThreatSimulationRequest(BaseModel):
    scenario_type: str  # replay_attack, ddos, sql_injection, consensus_stall
    intensity: str = "medium"  # low, medium, high
    target_component: str = "all"


class ThreatSimulationResponse(BaseModel):
    simulation_id: str
    correlation_id: str
    scenario_type: str
    status: str
    logs: List[str]
    detected_by_ids: bool
    evidence_hashes: List[str]


# US-64/US-74: Replay & Audit Schemas
class LedgerReplayRequest(BaseModel):
    election_id: UUID
    verify_signatures: bool = True


class LedgerReplayResponse(BaseModel):
    total_blocks: int
    valid_blocks: int
    invalid_blocks: int
    tip_hash: str
    recomputation_time_ms: float
    status: str  # clean, corrupted
    discrepancies: List[Dict[str, Any]]


class TimelineEvent(BaseModel):
    timestamp: datetime
    subsystem: str
    event_type: str
    reference_id: Optional[str] = None
    details_hash: Optional[str] = None


class TimelineReportResponse(BaseModel):
    election_id: Optional[UUID] = None
    generated_at: datetime
    total_events: int
    timeline_hash: str
    events: List[TimelineEvent]
    signature: str
    public_key: str
    artifact: Optional[str] = None


class AnomalyReportResponse(BaseModel):
    generated_at: datetime
    window_minutes: int
    anomalies: List[Dict[str, Any]]
    report_hash: str
    signature: str
    public_key: str
    artifact: Optional[str] = None


# Anonymous Voting Schemas

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
