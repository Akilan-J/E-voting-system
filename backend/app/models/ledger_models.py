"""Epic 3: Immutable Vote Ledger - SQLAlchemy Database Models

Defines the database schema for the blockchain ledger system.
Tables store blocks, entries, approvals, snapshots, and pruning records.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class LedgerNode(Base):
    """BFT consensus nodes participating in the ledger network"""
    __tablename__ = "ledger_nodes"

    node_id = Column(String(255), primary_key=True)
    public_key = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    last_height = Column(Integer, default=0)

class LedgerBlock(Base):
    """Blockchain blocks - each contains multiple vote entries"""
    __tablename__ = "ledger_blocks"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    height = Column(Integer, nullable=False, index=True)
    prev_hash = Column(Text, nullable=False)
    merkle_root = Column(Text, nullable=False)
    block_hash = Column(Text, unique=True, nullable=False)
    entry_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    commit_cert_hash = Column(Text, nullable=True)
    committed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('election_id', 'height', name='uq_election_height'),
    )

class LedgerEntry(Base):
    """Individual vote entries in the ledger (Merkle tree leaves)"""
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True)
    vote_id = Column(UUID(as_uuid=True), nullable=True)
    entry_hash = Column(Text, nullable=False, index=True)
    ciphertext_hash = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    block_height = Column(Integer, nullable=True, index=True)
    leaf_index = Column(Integer, nullable=True)

class LedgerApproval(Base):
    """BFT node approvals for blocks (signatures for quorum)"""
    __tablename__ = "ledger_approvals"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True)
    height = Column(Integer, nullable=False)
    block_hash = Column(Text, nullable=False)
    node_id = Column(String(255), nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('election_id', 'height', 'node_id', name='uq_election_height_node'),
    )

class LedgerSnapshot(Base):
    """Ledger state snapshots for efficient recovery"""
    __tablename__ = "ledger_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True)
    height = Column(Integer, nullable=False)
    tip_hash = Column(Text, nullable=False)
    snapshot_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    signed_by_node_id = Column(String(255))
    signature = Column(Text)

class LedgerEvent(Base):
    """Audit trail of ledger operations"""
    __tablename__ = "ledger_events"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True)
    event_type = Column(String(100), nullable=False)
    payload_hash = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    anchored_block_height = Column(Integer, nullable=True)

class LedgerPruning(Base):
    """Records of data pruning operations (removes old ciphertext)"""
    __tablename__ = "ledger_pruning"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), nullable=True)
    pruned_before_height = Column(Integer, nullable=False)
    policy = Column(Text, nullable=False)
    event_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
