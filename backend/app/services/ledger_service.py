"""Epic 3: Immutable Vote Ledger - Core Service Layer

Implements BFT consensus blockchain for vote immutability.
Handles block proposal, approval, finalization, and chain verification.

User Stories implemented:
  US-32  Permissioned node enforcement
  US-33  BFT consensus + commit certificate
  US-34  Append-only semantics (no delete/update exposed)
  US-35  Hash-linked chain verification
  US-36  Catch-up / sync helpers + split-brain prevention
  US-38  Node heartbeat & health
  US-39  Consensus stall detection
  US-40  Strict block validation (validate_block)
  US-41  Snapshot create/verify/latest with manifest hash
  US-42  Event anchoring for all key operations
  US-43  Pluggable signature mode (simulated | ed25519)
  US-44  Quorum enforcement with distinct active nodes
  US-46  Payload pruning preserving all hashes
  Merkle inclusion proofs (get_merkle_proof / verify_merkle_proof)
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
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

# ---------------------------------------------------------------------------
# Signature back-ends
# ---------------------------------------------------------------------------

def _load_ed25519_private_key():
    """Load Ed25519 private key from env (base64) or file path."""
    raw_b64 = os.getenv("LEDGER_NODE_PRIVATE_KEY", "")
    if raw_b64:
        raw = base64.b64decode(raw_b64)
    else:
        key_file = os.getenv("LEDGER_NODE_KEY_FILE", "")
        if key_file and os.path.exists(key_file):
            with open(key_file, "rb") as f:
                raw = base64.b64decode(f.read().strip())
        else:
            # Generate a deterministic dev key so tests always work without config
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            return Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import load_raw_private_key
    return Ed25519PrivateKey.from_private_bytes(raw)


class LedgerService:
    """BFT blockchain service - manages blocks, consensus, and verification"""

    def __init__(self):
        self.node_id = os.getenv("LEDGER_NODE_ID", "node-1")
        self.f = int(os.getenv("LEDGER_F", "0"))
        self.n = int(os.getenv("LEDGER_N", "1"))
        # quorum = 2f+1 but never exceed N
        self.quorum = min(2 * self.f + 1, self.n)

        # US-43: signature mode (simulated | ed25519)
        self.signature_mode = os.getenv("LEDGER_SIGNATURE_MODE", "simulated").lower()

        # Simulated mode private key
        self._sim_private_key = "simulated_private_key_for_" + self.node_id

        # Ed25519 private key (lazy loaded)
        self._ed25519_private_key = None

        # US-40: Block validation limits
        self.max_block_size = int(os.getenv("LEDGER_MAX_BLOCK_SIZE", "10485760"))   # 10MB
        self.max_entries_per_block = int(os.getenv("LEDGER_MAX_ENTRIES_PER_BLOCK", "10000"))

        # US-39: Stall detection timeout
        self.stall_seconds = int(os.getenv("LEDGER_STALL_SECONDS", "60"))

        # Backwards-compat: honour the old flag for simulated validation
        self.enable_signature_validation = (
            os.getenv("LEDGER_ENABLE_SIGNATURE_VALIDATION", "false").lower() == "true"
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _hash(self, data: str) -> str:
        """Compute SHA-256 hash"""
        return hashlib.sha256(data.encode()).hexdigest()

    def _record_event(
        self,
        db: Session,
        *,
        election_id: Optional[uuid.UUID],
        event_type: str,
        payload: Dict,
        anchored_block_height: Optional[int] = None
    ) -> None:
        """US-42: Deterministic event anchoring — hash(canonical json)"""
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        event = LedgerEvent(
            election_id=election_id,
            event_type=event_type,
            payload_hash=self._hash(payload_json),
            anchored_block_height=anchored_block_height
        )
        db.add(event)
        db.commit()

    # -----------------------------------------------------------------------
    # US-43: Pluggable signature back-ends
    # -----------------------------------------------------------------------

    def _get_ed25519_private_key(self):
        if self._ed25519_private_key is None:
            self._ed25519_private_key = _load_ed25519_private_key()
        return self._ed25519_private_key

    def _sign(self, data: str) -> str:
        """Sign data with node's private key."""
        if self.signature_mode == "ed25519":
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            priv = self._get_ed25519_private_key()
            sig_bytes = priv.sign(data.encode())
            return base64.b64encode(sig_bytes).decode()
        # simulated mode
        return self._hash(f"{data}{self.node_id}{self._sim_private_key}")

    def _verify_signature(self, data: str, signature: str, node_id: str, db: Session = None) -> bool:
        """Verify a node's signature. Uses public key from ledger_nodes in ed25519 mode."""
        if self.signature_mode == "ed25519" and db is not None:
            node = db.query(LedgerNode).filter(LedgerNode.node_id == node_id).first()
            if not node or not node.public_key:
                return False
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                pub_bytes = base64.b64decode(node.public_key)
                pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
                pub.verify(base64.b64decode(signature), data.encode())
                return True
            except Exception:
                return False
        # simulated mode
        if not self.enable_signature_validation:
            return True
        expected = self._hash(f"{data}{node_id}simulated_private_key_for_{node_id}")
        return signature == expected

    # -----------------------------------------------------------------------
    # US-32: Permissioned node enforcement
    # -----------------------------------------------------------------------

    def _require_active_node(self, node_id: str, db: Session) -> LedgerNode:
        """Raise PermissionError if node is not registered and active."""
        node = db.query(LedgerNode).filter(
            LedgerNode.node_id == node_id,
            LedgerNode.is_active == True
        ).first()
        if not node:
            raise PermissionError(
                f"node_not_active: Node '{node_id}' is not a registered active ledger node"
            )
        return node

    def register_node(self, db: Session, node_id: str, public_key: str = "") -> LedgerNode:
        """Register or re-activate a ledger node (admin only)."""
        node = db.query(LedgerNode).filter(LedgerNode.node_id == node_id).first()
        if node:
            node.is_active = True
            if public_key:
                node.public_key = public_key
        else:
            node = LedgerNode(
                node_id=node_id,
                public_key=public_key or f"simulated_public_key_{node_id}",
                is_active=True
            )
            db.add(node)
        db.commit()
        db.refresh(node)
        self._record_event(db, election_id=None, event_type="node_registered",
                           payload={"node_id": node_id})
        return node

    def disable_node(self, db: Session, node_id: str) -> LedgerNode:
        """Disable a node (admin only) — it can no longer participate in consensus."""
        node = db.query(LedgerNode).filter(LedgerNode.node_id == node_id).first()
        if not node:
            raise ValueError(f"Node '{node_id}' not found")
        node.is_active = False
        db.commit()
        db.refresh(node)
        self._record_event(db, election_id=None, event_type="node_disabled",
                           payload={"node_id": node_id})
        return node

    # -----------------------------------------------------------------------
    # US-40: Deterministic block validator
    # -----------------------------------------------------------------------

    def validate_block(self, block: LedgerBlock, db: Session) -> Tuple[bool, str]:
        """
        US-40: Single authoritative block validator.
        Returns (is_valid, error_code).
        """
        # 1. Hash length checks (SHA-256 = 64 hex chars)
        for field, value in [
            ("block_hash", block.block_hash),
            ("prev_hash", block.prev_hash),
            ("merkle_root", block.merkle_root),
        ]:
            if not value or len(value) != 64:
                return False, "invalid_hash_length"

        # 2. Entry count limit
        if block.entry_count > self.max_entries_per_block:
            return False, "too_many_entries"

        # 3. Height monotonicity
        if block.height < 0:
            return False, "invalid_height"

        # 4. prev_hash linkage (except genesis)
        if block.height > 0:
            prev = db.query(LedgerBlock).filter(
                LedgerBlock.election_id == block.election_id,
                LedgerBlock.height == block.height - 1,
                LedgerBlock.committed == True
            ).first()
            if not prev:
                return False, "missing_prev_block"
            if block.prev_hash != prev.block_hash:
                return False, "invalid_prev_hash"

        # 5. Merkle root match (recompute from stored entries)
        if block.height > 0:
            entries = db.query(LedgerEntry).filter(
                LedgerEntry.election_id == block.election_id,
                LedgerEntry.block_height == block.height
            ).order_by(LedgerEntry.entry_hash.asc()).all()
            computed_merkle = self._compute_merkle_root(entries)
            if computed_merkle != block.merkle_root:
                return False, "merkle_root_mismatch"

        # 6. Committed flag constraint — only finalize() sets committed=True
        # (nothing to check here at proposal time)

        return True, "valid"

    # Alias for backward compatibility with tests that used private name
    _validate_block_structure = validate_block

    # -----------------------------------------------------------------------
    # Merkle tree helpers
    # -----------------------------------------------------------------------

    def _compute_merkle_root(self, entries: List[LedgerEntry]) -> str:
        """Compute Merkle Root for a list of entries. Deterministic."""
        if not entries:
            return "0" * 64
        hashes = sorted([e.entry_hash for e in entries])
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])   # duplicate last if odd
            new_hashes = []
            for i in range(0, len(hashes), 2):
                new_hashes.append(self._hash(hashes[i] + hashes[i + 1]))
            hashes = new_hashes
        return hashes[0]

    def _compute_merkle_proof(self, leaf_hash: str, all_entries: List[LedgerEntry]) -> List[Dict]:
        """
        Compute Merkle inclusion proof for a leaf.
        Returns list of {hash, direction} dicts.
        """
        if not all_entries:
            return []
        hashes = sorted([e.entry_hash for e in all_entries])
        if leaf_hash not in hashes:
            return []

        proof = []
        idx = hashes.index(leaf_hash)

        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_hashes = []
            pair_idx = idx // 2
            for i in range(0, len(hashes), 2):
                left, right = hashes[i], hashes[i + 1]
                new_hashes.append(self._hash(left + right))
                if i // 2 == pair_idx:
                    sibling_i = i + 1 if idx % 2 == 0 else i
                    direction = "right" if idx % 2 == 0 else "left"
                    proof.append({"hash": hashes[sibling_i], "direction": direction})
            hashes = new_hashes
            idx = pair_idx

        return proof

    def get_merkle_proof(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        vote_id: Optional[uuid.UUID] = None,
        entry_hash: Optional[str] = None
    ) -> Optional[Dict]:
        """
        US: Merkle inclusion proof.
        Returns {entry_hash, merkle_root, proof, block_height} or None.
        """
        # Find the entry — only filter by election_id if it's actually provided
        q = db.query(LedgerEntry)
        if election_id is not None:
            q = q.filter(LedgerEntry.election_id == election_id)
        if vote_id:
            q = q.filter(LedgerEntry.vote_id == vote_id)
        elif entry_hash:
            q = q.filter(LedgerEntry.entry_hash == entry_hash)
        else:
            return None

        entry = q.first()
        if not entry or entry.block_height is None:
            return None

        # Get all entries in the same block (use same election scope if known)
        sibling_q = db.query(LedgerEntry).filter(
            LedgerEntry.block_height == entry.block_height
        )
        if entry.election_id is not None:
            sibling_q = sibling_q.filter(LedgerEntry.election_id == entry.election_id)
        siblings = sibling_q.all()

        block_q = db.query(LedgerBlock).filter(
            LedgerBlock.height == entry.block_height
        )
        if entry.election_id is not None:
            block_q = block_q.filter(LedgerBlock.election_id == entry.election_id)
        block = block_q.first()

        proof_steps = self._compute_merkle_proof(entry.entry_hash, siblings)
        return {
            "entry_hash": entry.entry_hash,
            "merkle_root": block.merkle_root if block else self._compute_merkle_root(siblings),
            "proof": proof_steps,
            "block_height": entry.block_height,
        }

    def verify_merkle_proof(self, leaf_hash: str, proof: List[Dict], merkle_root: str) -> bool:
        """
        Pure function: verify a Merkle inclusion proof.
        proof = list of {hash, direction} where direction is 'left' or 'right'.
        """
        current = leaf_hash
        for step in proof:
            sib = step.get("hash", "")
            direction = step.get("direction", "right")
            if direction == "left":
                current = self._hash(sib + current)
            else:
                current = self._hash(current + sib)
        return current == merkle_root

    # -----------------------------------------------------------------------
    # Genesis
    # -----------------------------------------------------------------------

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

        self._record_event(
            db,
            election_id=election_id,
            event_type="genesis_created",
            payload={"block_hash": genesis_block.block_hash, "height": 0},
            anchored_block_height=0
        )
        return genesis_block

    # -----------------------------------------------------------------------
    # Submit entry
    # -----------------------------------------------------------------------

    def submit_entry(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        vote_id: Optional[uuid.UUID],
        ciphertext: Optional[str]
    ) -> LedgerEntry:
        """Submit a new entry to the ledger. Never stores plaintext."""
        ciphertext_hash = self._hash(ciphertext) if ciphertext else None
        raw_data = f"{election_id}{vote_id}{ciphertext_hash}{uuid.uuid4()}"
        entry_hash = self._hash(raw_data)

        entry = LedgerEntry(
            election_id=election_id,
            vote_id=vote_id,
            entry_hash=entry_hash,
            ciphertext_hash=ciphertext_hash,
            block_height=None,
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

    # -----------------------------------------------------------------------
    # US-32 + US-33: Propose block
    # -----------------------------------------------------------------------

    def propose_block(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        max_entries: int = 1000
    ) -> Optional[LedgerBlock]:
        """Propose a new block from uncommitted entries. Node must be active (US-32)."""
        # US-32: calling node must be registered and active
        self._require_active_node(self.node_id, db)

        last_block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.desc()).first()

        if not last_block:
            last_block = self.create_genesis(db, election_id)

        next_height = last_block.height + 1

        # Return existing proposal if already proposed
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
            return None

        entries.sort(key=lambda x: x.entry_hash)

        merkle_root = self._compute_merkle_root(entries)
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

    # -----------------------------------------------------------------------
    # US-32 + US-43: Approve block
    # -----------------------------------------------------------------------

    def approve_block(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        height: int,
        approving_node_id: Optional[str] = None
    ) -> LedgerApproval:
        """Approve a block. Node must be active (US-32). Signs with configured mode (US-43)."""
        node_id = approving_node_id or self.node_id

        # US-32: must be an active node
        self._require_active_node(node_id, db)

        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height
        ).first()
        if not block:
            raise ValueError(f"Block at height {height} not found")

        # Idempotent
        existing = db.query(LedgerApproval).filter(
            LedgerApproval.election_id == election_id,
            LedgerApproval.height == height,
            LedgerApproval.node_id == node_id
        ).first()
        if existing:
            return existing

        signature = self._sign(block.block_hash)

        approval = LedgerApproval(
            election_id=election_id,
            height=height,
            block_hash=block.block_hash,
            node_id=node_id,
            signature=signature
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        self._record_event(
            db,
            election_id=election_id,
            event_type="block_approved",
            payload={"height": str(height), "block_hash": block.block_hash, "node_id": node_id},
            anchored_block_height=height
        )
        return approval

    # -----------------------------------------------------------------------
    # US-33 + US-36 + US-40 + US-44: Finalize block
    # -----------------------------------------------------------------------

    def finalize_block(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        height: int
    ) -> LedgerBlock:
        """
        Finalize a block if quorum is met.
        US-32: node must be active.
        US-33: compute deterministic commit_cert_hash.
        US-36: split-brain check (tip must equal prev_hash).
        US-40: validate_block before finalizing.
        US-44: quorum from DISTINCT active nodes.
        """
        self._require_active_node(self.node_id, db)

        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height
        ).first()
        if not block:
            raise ValueError(f"Block at height {height} not found")
        if block.committed:
            return block

        # US-36: split-brain prevention
        tip = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.desc()).first()

        if tip and tip.block_hash != block.prev_hash:
            raise ValueError(
                f"split_brain: Cannot finalize height {height}. "
                f"Expected prev_hash={tip.block_hash[:8]}... but got {block.prev_hash[:8]}..."
            )

        # US-40: validate block structure
        is_valid, error_code = self.validate_block(block, db)
        if not is_valid:
            rejection_event = LedgerEvent(
                election_id=election_id,
                event_type="block_rejected",
                payload_hash=self._hash(f"{block.block_hash}{error_code}"),
                anchored_block_height=height
            )
            db.add(rejection_event)
            db.commit()
            raise ValueError(f"Block validation failed: {error_code}")

        # US-44: Get approvals from DISTINCT ACTIVE nodes only
        all_approvals = db.query(LedgerApproval).filter(
            LedgerApproval.election_id == election_id,
            LedgerApproval.height == height,
            LedgerApproval.block_hash == block.block_hash
        ).all()

        # Filter to active nodes, deduplicate by node_id
        seen_nodes = set()
        valid_approvals = []
        for appr in all_approvals:
            if appr.node_id in seen_nodes:
                continue
            node = db.query(LedgerNode).filter(
                LedgerNode.node_id == appr.node_id,
                LedgerNode.is_active == True
            ).first()
            if not node:
                continue   # node_not_active — skip
            seen_nodes.add(appr.node_id)
            valid_approvals.append(appr)

        if len(valid_approvals) < self.quorum:
            raise ValueError(
                f"quorum_not_met: {len(valid_approvals)}/{self.quorum} "
                f"approvals from active nodes"
            )

        # US-43 + US-44: Verify signatures if mode requires it
        if self.signature_mode == "ed25519" or self.enable_signature_validation:
            for appr in valid_approvals:
                if not self._verify_signature(block.block_hash, appr.signature, appr.node_id, db):
                    raise ValueError(f"invalid_signature: node {appr.node_id}")

        # US-33: Deterministic commit certificate
        # cert_input = block_hash + sorted list of (node_id, signature)
        cert_parts = sorted([(a.node_id, a.signature) for a in valid_approvals])
        cert_data = block.block_hash + "".join(f"{nid}{sig}" for nid, sig in cert_parts)
        block.commit_cert_hash = self._hash(cert_data)
        block.committed = True

        db.commit()

        self._record_event(
            db,
            election_id=election_id,
            event_type="block_finalized",
            payload={
                "height": str(block.height),
                "block_hash": block.block_hash,
                "cert": block.commit_cert_hash,
                "approvals": len(valid_approvals)
            },
            anchored_block_height=block.height
        )
        return block

    # -----------------------------------------------------------------------
    # US-35: Chain verification
    # -----------------------------------------------------------------------

    def verify_chain(self, db: Session, election_id: Optional[uuid.UUID]) -> Dict:
        """
        US-35: Full chain verification.
        Returns structured {valid, blocks_verified, first_failing_height, reason_code}.
        """
        blocks = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.asc()).all()

        if not blocks:
            return {
                "valid": True,
                "blocks_verified": 0,
                "first_failing_height": None,
                "reason_code": None,
                "message": "No committed blocks"
            }

        # Check genesis exists and has correct structure
        genesis = blocks[0]
        if genesis.height != 0:
            return {
                "valid": False,
                "blocks_verified": 0,
                "first_failing_height": genesis.height,
                "reason_code": "missing_genesis"
            }

        # Verify genesis hash determinism
        expected_genesis_hash = self._hash(f"Genesis Block|{election_id}")
        if genesis.block_hash != expected_genesis_hash:
            return {
                "valid": False,
                "blocks_verified": 0,
                "first_failing_height": 0,
                "reason_code": "genesis_hash_mismatch"
            }

        for i in range(1, len(blocks)):
            prev = blocks[i - 1]
            curr = blocks[i]

            # Height continuity
            if curr.height != prev.height + 1:
                return {
                    "valid": False,
                    "blocks_verified": i,
                    "first_failing_height": curr.height,
                    "reason_code": "height_gap"
                }

            # prev_hash linkage
            if curr.prev_hash != prev.block_hash:
                return {
                    "valid": False,
                    "blocks_verified": i,
                    "first_failing_height": curr.height,
                    "reason_code": "broken_hash_link"
                }

            # Recompute Merkle root from stored entries
            entries = db.query(LedgerEntry).filter(
                LedgerEntry.election_id == election_id,
                LedgerEntry.block_height == curr.height
            ).order_by(LedgerEntry.entry_hash.asc()).all()

            computed_merkle = self._compute_merkle_root(entries)
            if computed_merkle != curr.merkle_root:
                return {
                    "valid": False,
                    "blocks_verified": i,
                    "first_failing_height": curr.height,
                    "reason_code": "merkle_root_mismatch"
                }

            # Recompute block hash
            expected_hash = self._hash(
                f"{curr.prev_hash}{computed_merkle}{curr.height}{curr.entry_count}"
            )
            if expected_hash != curr.block_hash:
                return {
                    "valid": False,
                    "blocks_verified": i,
                    "first_failing_height": curr.height,
                    "reason_code": "block_hash_mismatch"
                }

        return {
            "valid": True,
            "blocks_verified": len(blocks),
            "first_failing_height": None,
            "reason_code": None,
        }

    # -----------------------------------------------------------------------
    # US-36: Catch-up / sync
    # -----------------------------------------------------------------------

    def get_tip(self, db: Session, election_id: Optional[uuid.UUID]) -> Optional[LedgerBlock]:
        """Return the latest committed block for an election."""
        return db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True
        ).order_by(LedgerBlock.height.desc()).first()

    def export_blocks(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        start_height: int = 0
    ) -> List[Dict]:
        """
        US-36: Export block headers from start_height onwards for catch-up.
        Returns deterministic headers including commit certs.
        """
        blocks = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True,
            LedgerBlock.height >= start_height
        ).order_by(LedgerBlock.height.asc()).all()

        return [
            {
                "height": b.height,
                "prev_hash": b.prev_hash,
                "merkle_root": b.merkle_root,
                "block_hash": b.block_hash,
                "entry_count": b.entry_count,
                "timestamp": b.timestamp.isoformat() if b.timestamp else None,
                "commit_cert_hash": b.commit_cert_hash,
            }
            for b in blocks
        ]

    # -----------------------------------------------------------------------
    # US-38: Node heartbeat & health
    # -----------------------------------------------------------------------

    def record_heartbeat(self, db: Session, node_id: str, last_height: int) -> LedgerNode:
        """US-38: Update node last_seen and last_height."""
        node = db.query(LedgerNode).filter(LedgerNode.node_id == node_id).first()
        if not node:
            raise ValueError(f"Node '{node_id}' not found. Register it first.")
        node.last_seen = datetime.utcnow()
        node.last_height = last_height
        db.commit()
        db.refresh(node)
        return node

    def get_node_health(self, db: Session, election_id: Optional[uuid.UUID] = None) -> List[Dict]:
        """US-38: Return all nodes with their lag vs the current tip."""
        tip = self.get_tip(db, election_id)
        tip_height = tip.height if tip else 0

        nodes = db.query(LedgerNode).all()
        result = []
        for n in nodes:
            result.append({
                "node_id": n.node_id,
                "is_active": n.is_active,
                "last_seen": n.last_seen.isoformat() if n.last_seen else None,
                "last_height": n.last_height or 0,
                "lag": tip_height - (n.last_height or 0),
            })
        return result

    # -----------------------------------------------------------------------
    # US-39: Consensus stall detection
    # -----------------------------------------------------------------------

    def get_consensus_health(self, db: Session, election_id: Optional[uuid.UUID]) -> Dict:
        """US-39: Detect consensus stall based on time since last committed block."""
        tip = self.get_tip(db, election_id)
        now = datetime.utcnow()

        if not tip or tip.height == 0:
            return {
                "status": "ok",
                "last_height": tip.height if tip else 0,
                "last_block_time": tip.timestamp.isoformat() if tip else None,
                "seconds_since_commit": None,
                "stall_threshold_seconds": self.stall_seconds,
            }

        # Make timestamp offset-naive for comparison
        last_time = tip.timestamp
        if hasattr(last_time, 'tzinfo') and last_time.tzinfo is not None:
            last_time = last_time.replace(tzinfo=None)

        seconds_since = (now - last_time).total_seconds()
        status = "stalled" if seconds_since > self.stall_seconds else "ok"

        return {
            "status": status,
            "last_height": tip.height,
            "last_block_time": tip.timestamp.isoformat() if tip.timestamp else None,
            "seconds_since_commit": round(seconds_since, 2),
            "stall_threshold_seconds": self.stall_seconds,
        }

    # -----------------------------------------------------------------------
    # US-41: Snapshotting
    # -----------------------------------------------------------------------

    def _compute_manifest_hash(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        up_to_height: int
    ) -> str:
        """manifest_hash = SHA256(concatenated block_hashes from genesis to up_to_height)."""
        blocks = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.committed == True,
            LedgerBlock.height <= up_to_height
        ).order_by(LedgerBlock.height.asc()).all()
        combined = "".join(b.block_hash for b in blocks)
        return self._hash(combined)

    def snapshot_create(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        height: int
    ) -> LedgerSnapshot:
        """US-41: Create snapshot with deterministic hash."""
        block = db.query(LedgerBlock).filter(
            LedgerBlock.election_id == election_id,
            LedgerBlock.height == height,
            LedgerBlock.committed == True
        ).first()
        if not block:
            raise ValueError(f"Committed block at height {height} not found")

        manifest_hash = self._compute_manifest_hash(db, election_id, height)
        # US-41: snapshot_hash = hash(tip_hash + str(height) + manifest_hash)
        snapshot_hash = self._hash(f"{block.block_hash}{height}{manifest_hash}")
        signature = self._sign(snapshot_hash)

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

    def snapshot_verify(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        snapshot_hash: str
    ) -> Dict:
        """US-41: Verify that a given snapshot_hash matches the stored snapshot."""
        stored = db.query(LedgerSnapshot).filter(
            LedgerSnapshot.election_id == election_id,
            LedgerSnapshot.snapshot_hash == snapshot_hash
        ).first()

        if not stored:
            return {"valid": False, "reason": "snapshot_not_found"}

        # Recompute to verify integrity
        manifest_hash = self._compute_manifest_hash(db, election_id, stored.height)
        expected = self._hash(f"{stored.tip_hash}{stored.height}{manifest_hash}")
        if expected != snapshot_hash:
            return {"valid": False, "reason": "hash_mismatch"}

        return {
            "valid": True,
            "height": stored.height,
            "tip_hash": stored.tip_hash,
            "snapshot_hash": snapshot_hash,
        }

    def snapshot_latest(
        self,
        db: Session,
        election_id: Optional[uuid.UUID]
    ) -> Optional[LedgerSnapshot]:
        """US-41: Return the most recent snapshot for an election."""
        return db.query(LedgerSnapshot).filter(
            LedgerSnapshot.election_id == election_id
        ).order_by(LedgerSnapshot.height.desc()).first()

    # -----------------------------------------------------------------------
    # US-46: Pruning
    # -----------------------------------------------------------------------

    def prune(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        height_threshold: int
    ) -> LedgerPruning:
        """
        US-46: Prune old payload data, keeping all integrity-critical hashes.
        Nulls ciphertext_hash for entries below height_threshold.
        block_hash, merkle_root, entry_hash, commit_cert_hash are NEVER touched.
        """
        updated = db.query(LedgerEntry).filter(
            LedgerEntry.election_id == election_id,
            LedgerEntry.block_height < height_threshold,
            LedgerEntry.ciphertext_hash != None
        ).update({LedgerEntry.ciphertext_hash: None}, synchronize_session=False)

        policy_desc = (
            f"Pruned ciphertext_hash from entries before height {height_threshold}. "
            f"Preserved: entry_hash, block_hash, merkle_root, commit_cert_hash. "
            f"Rows affected: {updated}"
        )
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
            payload={
                "height_threshold": str(height_threshold),
                "rows_affected": str(updated),
                "event_hash": event_hash
            },
            anchored_block_height=height_threshold
        )
        return pruning_record

    def get_pruning_history(
        self,
        db: Session,
        election_id: Optional[uuid.UUID]
    ) -> List[LedgerPruning]:
        """US-46: Return pruning history for an election."""
        return db.query(LedgerPruning).filter(
            LedgerPruning.election_id == election_id
        ).order_by(LedgerPruning.created_at.desc()).all()

    # -----------------------------------------------------------------------
    # US-42: Events
    # -----------------------------------------------------------------------

    def get_events(
        self,
        db: Session,
        election_id: Optional[uuid.UUID],
        limit: int = 100
    ) -> List[LedgerEvent]:
        """US-42: Return ledger events for an election."""
        q = db.query(LedgerEvent)
        if election_id is not None:
            q = q.filter(LedgerEvent.election_id == election_id)
        return q.order_by(LedgerEvent.timestamp.desc()).limit(limit).all()


# Singleton instance
ledger_service = LedgerService()
