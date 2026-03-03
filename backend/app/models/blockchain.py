from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import uuid

class BlockHeader(BaseModel):
    """Block Header model"""
    height: int
    timestamp: datetime
    prev_hash: str
    merkle_root: str
    block_hash: str
    entry_count: int
    commit_cert_hash: Optional[str] = None

class LedgerEntryDTO(BaseModel):
    """Data Transfer Object for Ledger Entries (no ciphertext exposed)"""
    entry_hash: str
    vote_id: Optional[uuid.UUID] = None
    leaf_index: Optional[int] = None
    block_height: Optional[int] = None

class ApprovalDTO(BaseModel):
    """Data Transfer Object for Block Approvals"""
    node_id: str
    signature: str

class SnapshotDTO(BaseModel):
    """Data Transfer Object for Ledger Snapshots"""
    height: int
    tip_hash: str
    snapshot_hash: str
    signature: str

# --- New DTOs for Epic 3 completion ---

class NodeDTO(BaseModel):
    """Ledger node registration/health info"""
    node_id: str
    public_key: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_height: Optional[int] = None
    lag: Optional[int] = None  # blocks behind tip

class NodeRegisterRequest(BaseModel):
    node_id: str
    public_key: Optional[str] = ""

class NodeDisableRequest(BaseModel):
    node_id: str

class HeartbeatRequest(BaseModel):
    node_id: str
    last_height: int

class SnapshotVerifyRequest(BaseModel):
    election_id: Optional[uuid.UUID] = None
    snapshot_hash: str

class MerkleProofStep(BaseModel):
    hash: str
    direction: str  # "left" or "right"

class MerkleProofResponse(BaseModel):
    entry_hash: str
    merkle_root: str
    proof: List[MerkleProofStep]
    valid: bool

class ConsensusHealthResponse(BaseModel):
    status: str  # "ok" or "stalled"
    last_height: Optional[int] = None
    last_block_time: Optional[datetime] = None
    seconds_since_commit: Optional[float] = None
    stall_threshold_seconds: int

class PruningHistoryItem(BaseModel):
    id: int
    pruned_before_height: int
    policy: str
    event_hash: str
    created_at: datetime

class EventDTO(BaseModel):
    id: int
    election_id: Optional[uuid.UUID] = None
    event_type: str
    payload_hash: str
    timestamp: datetime
    anchored_block_height: Optional[int] = None

class TipResponse(BaseModel):
    election_id: Optional[uuid.UUID] = None
    height: int
    block_hash: str
    timestamp: datetime
