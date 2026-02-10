"""Epic 3: Immutable Vote Ledger - Core Service Layer

Implements BFT consensus blockchain for vote immutability.
Handles block proposal, approval, finalization, and chain verification.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from app.models.ledger_models import (
    LedgerNode, LedgerBlock, LedgerEntry, LedgerApproval, LedgerSnapshot, 
    LedgerEvent, LedgerPruning
)
from app.models.blockchain import BlockHeader

logger = logging.getLogger(__name__)

class LedgerService:
    """BFT blockchain service - manages blocks, consensus, and verification"""


    def __init__(self):
        self.node_id = os.getenv("LEDGER_NODE_ID", "node-1")
        self.f = int(os.getenv("LEDGER_F", "1"))
        self.n = int(os.getenv("LEDGER_N", "4"))
        self.quorum = 2 * self.f + 1
        # In a real system, private keys would be in HSM. Here we simulate.
        self.private_key = "simulated_private_key_for_" + self.node_id
        
        # US-40: Block validation limits
        self.max_block_size = int(os.getenv("LEDGER_MAX_BLOCK_SIZE", "10485760"))  # 10MB
        self.max_entries_per_block = int(os.getenv("LEDGER_MAX_ENTRIES_PER_BLOCK", "10000"))
        self.enable_signature_validation = os.getenv("LEDGER_ENABLE_SIGNATURE_VALIDATION", "false").lower() == "true"
        
        # US-33: Consensus configuration
        self.consensus_timeout = int(os.getenv("LEDGER_CONSENSUS_TIMEOUT_SECONDS", "300"))

    def _hash(self, data: str) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(data.encode()).hexdigest()

    def _record_event(
        self,
        db: Session,
        *,
        election_id: Optional[uuid.UUID],
        event_type: str,
        payload: Dict[str, Optional[str]],
        anchored_block_height: Optional[int] = None
    ) -> None:
        payload_json = json.dumps(payload, sort_keys=True)
        event = LedgerEvent(
            election_id=election_id,
            event_type=event_type,
            payload_hash=self._hash(payload_json),
            anchored_block_height=anchored_block_height
        )
        db.add(event)
        db.commit()
    
    def _sign(self, data: str) -> str:
        """Sign data with node's private key (simulated)"""
        # In production: use cryptography library with real keys
        return self._hash(f"{data}{self.node_id}{self.private_key}")
    
    def _verify_signature(self, data: str, signature: str, node_id: str) -> bool:
        """Verify signature (simulated for demo, real in production)"""
        if not self.enable_signature_validation:
            return True  # Skip validation if disabled
        
        # For demo: simple hash-based verification
        # Production: use cryptography library with public key verification
        expected = self._hash(f"{data}{node_id}simulated_private_key_for_{node_id}")
        return signature == expected
    
    def _validate_block_structure(self, block: LedgerBlock, db: Session) -> Tuple[bool, str]:
        """US-40: Validate block structure and rules"""
        # Check hash length (SHA-256 = 64 hex chars)
        if len(block.block_hash) != 64 or len(block.prev_hash) != 64 or len(block.merkle_root) != 64:
            return (False, "invalid_hash_length")

        # Check entry count
        if block.entry_count > self.max_entries_per_block:
            return (False, "too_many_entries")

        # Check height monotonicity
        if block.height < 0:
            return (False, "invalid_height")
        
        # Check prev_hash linkage (except genesis)
        if block.height > 0:
            prev_block = db.query(LedgerBlock).filter(
                LedgerBlock.election_id == block.election_id,
                LedgerBlock.height == block.height - 1
            ).first()
            
            if not prev_block:
                return (False, "missing_prev_block")
            
            if block.prev_hash != prev_block.block_hash:
                return (False, "invalid_prev_hash")
        
        # Check entry count
        if block.entry_count > self.max_entries_per_block:
            return (False, "too_many_entries")

        return (True, "valid")

    def _compute_merkle_root(self, entries: List[LedgerEntry]) -> str:
        """Compute Merkle Root for a list of entries"""
        if not entries:
            return "0" * 64
        
        # Sort by entry_hash to ensure determinism
        hashes = sorted([e.entry_hash for e in entries])
        
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1]) # Duplicate last if odd
            
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i+1]
                new_hashes.append(self._hash(combined))
            hashes = new_hashes
        
        return hashes[0]

    def create_genesis(self, db: Session, election_id: Optional[uuid.UUID] = None) -> LedgerBlock:
        """Create Genesis Block (Height 0)"""
        existing = db.query(LedgerBlock).filter(
            LedgerBlock.height == 0,
            LedgerBlock.election_id == election_id
        ).first()
        
        if existing:
            return existing
            
        logger.info(f"Creating Genesis Block for election {election_id}")
        
        genesis_block = LedgerBlock(
            election_id=election_id,
            height=0,
            prev_hash="0" * 64,
            merkle_root="0" * 64,
            block_hash=self._hash(f"Genesis Block|{election_id}"),
            entry_count=0,
            committed=True,
            commit_cert_hash="Genesis Cert"
        )
        db.add(genesis_block)
        db.commit()
        db.refresh(genesis_block)
        return genesis_block

    def submit_entry(self, db: Session, election_id: Optional[uuid.UUID], 
                     vote_id: Optional[uuid.UUID], ciphertext: Optional[str]) -> LedgerEntry:
        """Submit a new entry to the ledger"""
        # Calculate hashes
        ciphertext_hash = self._hash(ciphertext) if ciphertext else None
        
        # Entry hash: SHA256(election_id + vote_id + ciphertext_hash + nonce_ish)
        # Using uuid.uuid4() as nonce/unique factor
        raw_data = f"{election_id}{vote_id}{ciphertext_hash}{uuid.uuid4()}"
        entry_hash = self._hash(raw_data)
        
        entry = LedgerEntry(
            election_id=election_id,
            vote_id=vote_id,
            entry_hash=entry_hash,
            ciphertext_hash=ciphertext_hash,
            block_height=None, # Uncommitted
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        self._record_event(
            db,
            election_id=election_id,
            event_type="entry_submitted",
            payload={"entry_hash": entry.entry_hash, "vote_id": str(vote_id) if vote_id else None}
        )
        return entry

    def propose_block(self, db: Session, election_id: Optional[uuid.UUID], max_entries: int = 1000) -> LedgerBlock:
        """Propose a new block from uncommitted entries"""
        # Get last committed block
        last_block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.desc()).first()
        
        if not last_block:
            last_block = self.create_genesis(db, election_id)

        next_height = last_block.height + 1
        
        # Check if block already proposed at this height
        existing_proposal = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == next_height
        ).first()
        
        if existing_proposal:
            return existing_proposal

        # Gather uncommitted entries
        entries = db.query(LedgerEntry).filter(
            LedgerEntry.election_id == election_id,
            LedgerEntry.block_height == None
        ).limit(max_entries).all()
        
        if not entries:
            # No entries to block, return None or wait? 
            # For this demo, let's allow empty blocks or just return None?
            # Usually we wait. Return None.
            return None
        
        # Deterministic sort
        entries.sort(key=lambda x: x.entry_hash)
        
        merkle_root = self._compute_merkle_root(entries)
        
        # Block Hash input: prev_hash + merkle_root + height + entry_count
        block_data = f"{last_block.block_hash}{merkle_root}{next_height}{len(entries)}"
        block_hash = self._hash(block_data)
        
        new_block = LedgerBlock(
            election_id=election_id,
            height=next_height,
            prev_hash=last_block.block_hash,
            merkle_root=merkle_root,
            block_hash=block_hash,
            entry_count=len(entries),
            committed=False
        )
        db.add(new_block)
        
        # Pin entries to this block
        for i, entry in enumerate(entries):
            entry.block_height = next_height
            entry.leaf_index = i
            
        db.commit()
        db.refresh(new_block)

        self._record_event(
            db,
            election_id=election_id,
            event_type="block_proposed",
            payload={"height": str(new_block.height), "block_hash": new_block.block_hash},
            anchored_block_height=new_block.height
        )
        
        return new_block

    def approve_block(self, db: Session, election_id: Optional[uuid.UUID], height: int) -> LedgerApproval:
        """Approve a block (Sign it)"""
        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height
        ).first()
        
        if not block:
            raise ValueError(f"Block at height {height} not found")
        
        # Check if already approved
        existing = db.query(LedgerApproval).filter(
            LedgerApproval.election_id == election_id,
            LedgerApproval.height == height,
            LedgerApproval.node_id == self.node_id
        ).first()
        
        if existing:
            return existing

        # Sign logic (using _sign method)
        signature = self._sign(block.block_hash)
        
        approval = LedgerApproval(
            election_id=election_id,
            height=height,
            block_hash=block.block_hash,
            node_id=self.node_id,
            signature=signature
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        self._record_event(
            db,
            election_id=election_id,
            event_type="block_approved",
            payload={"height": str(height), "block_hash": block.block_hash, "node_id": self.node_id},
            anchored_block_height=height
        )
        return approval

    def finalize_block(self, db: Session, election_id: Optional[uuid.UUID], height: int) -> LedgerBlock:
        """Finalize a block if Quorum is met (US-33, US-40 enhanced)"""
        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height
        ).first()
        
        if not block:
            raise ValueError(f"Block at height {height} not found")
        
        if block.committed:
            return block

        # US-40: Validate block structure before finalization
        is_valid, error_code = self._validate_block_structure(block, db)
        if not is_valid:
            logger.error(f"Block validation failed: {error_code} for block {height}")
            # Record rejection event
            rejection_event = LedgerEvent(
                election_id=election_id,
                event_type="block_rejected",
                payload_hash=self._hash(f"{block.block_hash}{error_code}"),
                anchored_block_height=height
            )
            db.add(rejection_event)
            db.commit()
            raise ValueError(f"Block validation failed: {error_code}")

        # Count approvals
        approvals = db.query(LedgerApproval).filter(
            LedgerApproval.election_id == election_id,
            LedgerApproval.height == height,
            LedgerApproval.block_hash == block.block_hash
        ).all()
        
        if len(approvals) < self.quorum:
            raise ValueError(f"Quorum not met: {len(approvals)}/{self.quorum}")

        # US-40: Verify signatures if enabled
        if self.enable_signature_validation:
            for approval in approvals:
                if not self._verify_signature(block.block_hash, approval.signature, approval.node_id):
                    logger.error(f"Invalid signature from node {approval.node_id} for block {height}")
                    raise ValueError(f"Invalid signature from node {approval.node_id}")

        # Update block
        cert_data = "".join(sorted([a.signature for a in approvals]))
        block.commit_cert_hash = self._hash(cert_data)
        block.committed = True
        
        # Entries are already pinned in propose_block
        
        db.commit()
        self._record_event(
            db,
            election_id=election_id,
            event_type="block_finalized",
            payload={"height": str(block.height), "block_hash": block.block_hash, "cert": block.commit_cert_hash},
            anchored_block_height=block.height
        )
        return block

    def snapshot_create(self, db: Session, election_id: Optional[uuid.UUID], height: int) -> LedgerSnapshot:
        """Create a snapshot at a specific height (US-41)"""
        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height,
            LedgerBlock.committed == True
        ).first()
        
        if not block:
            raise ValueError(f"Committed block at height {height} not found")
            
        # Snapshot content: tip_hash + height
        snapshot_data = f"{block.block_hash}{height}{election_id}"
        snapshot_hash = self._hash(snapshot_data)
        
        # Sign it
        signature = self._hash(f"{snapshot_hash}{self.private_key}")
        
        snapshot = LedgerSnapshot(
            election_id=election_id,
            height=height,
            tip_hash=block.block_hash,
            snapshot_hash=snapshot_hash,
            signed_by_node_id=self.node_id,
            signature=signature
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        self._record_event(
            db,
            election_id=election_id,
            event_type="snapshot_created",
            payload={"height": str(height), "snapshot_hash": snapshot_hash},
            anchored_block_height=height
        )
        return snapshot

    def prune(self, db: Session, election_id: Optional[uuid.UUID], height_threshold: int) -> LedgerPruning:
        """Prune old payload data, keeping headers (US-46)"""
        # Delete ciphertext_hash from old entries?
        # Requirement: "archive/delete old payload fields ONLY (e.g., ciphertext_hash) but preserve entry_hash + block headers"
        
        updated = db.query(LedgerEntry).filter(
            LedgerEntry.election_id == election_id,
            LedgerEntry.block_height < height_threshold,
            LedgerEntry.ciphertext_hash != None
        ).update({LedgerEntry.ciphertext_hash: None}, synchronize_session=False)
        
        policy_desc = f"Pruned payloads before height {height_threshold}"
        event_hash = self._hash(f"{election_id}{height_threshold}{updated}")
        
        pruning_record = LedgerPruning(
            election_id=election_id,
            pruned_before_height=height_threshold,
            policy=policy_desc,
            event_hash=event_hash
        )
        db.add(pruning_record)
        db.commit()
        self._record_event(
            db,
            election_id=election_id,
            event_type="ledger_pruned",
            payload={"height_threshold": str(height_threshold), "event_hash": event_hash},
            anchored_block_height=height_threshold
        )
        return pruning_record

    def verify_chain(self, db: Session, election_id: Optional[uuid.UUID]) -> Dict:
        """Verify the integrity of the blockchain (US-35)"""
        blocks = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.asc()).all()
        
        # Check Genesis
        if not blocks or blocks[0].height != 0:
            return {"valid": False, "reason": "Missing Genesis"}
            
        for i in range(1, len(blocks)):
            prev = blocks[i-1]
            curr = blocks[i]
            
            # Link check
            if curr.prev_hash != prev.block_hash:
                return {"valid": False, "reason": f"Broken link at height {curr.height}"}
            
            # Hash check
            # Recompute block hash
            # We need to trust the merkle_root stored? Or recompute it from entries?
            # Ideally recompute from entries.
            entries = db.query(LedgerEntry).filter(
                LedgerEntry.election_id == election_id,
                LedgerEntry.block_height == curr.height
            ).order_by(LedgerEntry.entry_hash.asc()).all()
            
            computed_merkle = self._compute_merkle_root(entries)
            if computed_merkle != curr.merkle_root:
                 return {"valid": False, "reason": f"Merkle mismatch at height {curr.height}"}
                 
            expected_hash = self._hash(f"{curr.prev_hash}{computed_merkle}{curr.height}{curr.entry_count}")
            if expected_hash != curr.block_hash:
                 return {"valid": False, "reason": f"Hash mismatch at height {curr.height}"}
                 
        return {"valid": True, "blocks_verified": len(blocks)}

ledger_service = LedgerService()
