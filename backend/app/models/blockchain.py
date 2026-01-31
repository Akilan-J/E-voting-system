from pydantic import BaseModel
from typing import Optional, List
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
    """Data Transfer Object for Ledger Entries"""
    entry_hash: str
    ciphertext_hash: Optional[str] = None
    vote_id: Optional[uuid.UUID] = None
    leaf_index: Optional[int] = None

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
