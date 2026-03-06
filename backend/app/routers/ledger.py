"""Epic 3: Immutable Vote Ledger - API Router

Exposes REST endpoints for blockchain operations.
All write endpoints require authentication (RBAC).
All read endpoints are rate-limited for public access (US-45).

User Stories covered:
  US-32  /nodes/register, /nodes/disable
  US-33  /propose, /approve, /finalize (BFT pipeline)
  US-34  No update/delete endpoints for committed blocks
  US-35  /verify-chain (structured pass/fail)
  US-36  /blocks/from, /tip, /compare-tip
  US-37  /blocks/{height}, /entries
  US-38  /node/heartbeat, /node/health
  US-39  /consensus/health
  US-40  Validation enforced inside service
  US-41  /snapshot/create, /snapshot/verify, /snapshot/latest
  US-42  /events
  US-43  Signature mode via env
  US-44  Quorum enforced in service
  US-45  Rate limiting on all read endpoints
  US-46  /prune, /pruning/history
  Merkle /proof
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os

from app.models.database import get_db
from app.models.blockchain import (
    BlockHeader, LedgerEntryDTO,
    NodeDTO, NodeRegisterRequest, NodeDisableRequest,
    HeartbeatRequest, SnapshotVerifyRequest,
    MerkleProofResponse, MerkleProofStep,
    ConsensusHealthResponse, PruningHistoryItem,
    EventDTO, TipResponse,
)
from app.services.ledger_service import ledger_service
from app.models.ledger_models import LedgerBlock, LedgerEntry, LedgerNode
from app.utils.auth_utils import require_roles
from app.models.auth_models import User

# US-45: Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse

enable_rate_limiting = os.getenv("LEDGER_ENABLE_RATE_LIMITING", "true").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=enable_rate_limiting)

router = APIRouter()

# ============================================================
# US-45: Public read endpoints (all rate-limited)
# ============================================================

@router.get("/blocks", response_model=List[BlockHeader])
@limiter.limit("100/minute")
async def list_blocks(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List committed blocks from the ledger (rate-limited, public)."""
    query = db.query(LedgerBlock)
    if election_id:
        query = query.filter(LedgerBlock.election_id == election_id)
    blocks = query.filter(LedgerBlock.committed == True).order_by(
        LedgerBlock.height.asc()
    ).limit(limit).all()

    return [
        BlockHeader(
            height=b.height,
            timestamp=b.timestamp,
            prev_hash=b.prev_hash,
            merkle_root=b.merkle_root,
            block_hash=b.block_hash,
            entry_count=b.entry_count,
            commit_cert_hash=b.commit_cert_hash
        ) for b in blocks
    ]


@router.get("/blocks/from", response_model=List[dict])
@limiter.limit("60/minute")
async def blocks_from(
    request: Request,
    start_height: int = Query(0, ge=0),
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-36: Export block headers from start_height for catch-up."""
    return ledger_service.export_blocks(db, election_id, start_height)


@router.get("/blocks/{height}", response_model=BlockHeader)
@limiter.limit("100/minute")
async def get_block_by_height(
    request: Request,
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-37: Get a specific block by height."""
    q = db.query(LedgerBlock).filter(
        LedgerBlock.height == height,
        LedgerBlock.committed == True
    )
    if election_id:
        q = q.filter(LedgerBlock.election_id == election_id)
    block = q.first()
    if not block:
        raise HTTPException(status_code=404, detail=f"No committed block at height {height}")
    return BlockHeader(
        height=block.height,
        timestamp=block.timestamp,
        prev_hash=block.prev_hash,
        merkle_root=block.merkle_root,
        block_hash=block.block_hash,
        entry_count=block.entry_count,
        commit_cert_hash=block.commit_cert_hash
    )


@router.get("/entries", response_model=List[LedgerEntryDTO])
@limiter.limit("60/minute")
async def list_entries(
    request: Request,
    block_height: Optional[int] = None,
    election_id: Optional[uuid.UUID] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """US-37: List entries with only hashes/metadata (no ciphertext). Rate-limited."""
    q = db.query(LedgerEntry)
    if election_id:
        q = q.filter(LedgerEntry.election_id == election_id)
    if block_height is not None:
        q = q.filter(LedgerEntry.block_height == block_height)
    entries = q.order_by(LedgerEntry.leaf_index.asc()).limit(limit).all()
    return [
        LedgerEntryDTO(
            entry_hash=e.entry_hash,
            vote_id=e.vote_id,
            leaf_index=e.leaf_index,
            block_height=e.block_height,
            # ciphertext_hash intentionally NOT included — US-34, US-45
        )
        for e in entries
    ]


@router.get("/tip")
@limiter.limit("100/minute")
async def get_tip(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-36: Get the latest committed block tip."""
    tip = ledger_service.get_tip(db, election_id)
    if not tip:
        return {"height": -1, "block_hash": None}
    return {
        "election_id": str(election_id) if election_id else None,
        "height": tip.height,
        "block_hash": tip.block_hash,
        "timestamp": tip.timestamp.isoformat() if tip.timestamp else None,
    }


@router.get("/compare-tip")
@limiter.limit("100/minute")
async def compare_tip(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-36: Compare tip — returns tip hash + height for external sync."""
    tip = ledger_service.get_tip(db, election_id)
    return {
        "election_id": str(election_id) if election_id else None,
        "height": tip.height if tip else -1,
        "block_hash": tip.block_hash if tip else None,
    }


@router.get("/verify-chain")
@limiter.limit("30/minute")
async def verify_chain(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-35: Verify chain integrity with structured response."""
    return ledger_service.verify_chain(db, election_id)


@router.get("/node/health", response_model=List[NodeDTO])
@limiter.limit("60/minute")
async def node_health(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-38: Get health of all ledger nodes vs current tip."""
    health = ledger_service.get_node_health(db, election_id)
    return [NodeDTO(**n) for n in health]


@router.get("/consensus/health")
@limiter.limit("60/minute")
async def consensus_health(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-39: Detect consensus stall (ok/stalled)."""
    return ledger_service.get_consensus_health(db, election_id)


@router.get("/snapshot/latest")
@limiter.limit("60/minute")
async def snapshot_latest(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-41: Get the most recent snapshot."""
    snap = ledger_service.snapshot_latest(db, election_id)
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshots found")
    return {
        "height": snap.height,
        "tip_hash": snap.tip_hash,
        "snapshot_hash": snap.snapshot_hash,
        "created_at": snap.created_at.isoformat() if snap.created_at else None,
        "signed_by_node_id": snap.signed_by_node_id,
    }


@router.get("/events", response_model=List[EventDTO])
@limiter.limit("60/minute")
async def list_events(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db)
):
    """US-42: List ledger events (audit trail, no vote content)."""
    events = ledger_service.get_events(db, election_id, limit)
    return [
        EventDTO(
            id=e.id,
            election_id=e.election_id,
            event_type=e.event_type,
            payload_hash=e.payload_hash,
            timestamp=e.timestamp,
            anchored_block_height=e.anchored_block_height,
        )
        for e in events
    ]


@router.get("/proof", response_model=MerkleProofResponse)
@limiter.limit("60/minute")
async def merkle_proof(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    vote_id: Optional[uuid.UUID] = None,
    entry_hash: Optional[str] = None,
    receipt_hash: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Merkle inclusion proof for a vote entry. Accepts vote_id, entry_hash, or receipt_hash."""
    # If receipt_hash provided, resolve it to a vote_id first
    if receipt_hash and not vote_id and not entry_hash:
        from app.models.database import EncryptedVote
        vote = db.query(EncryptedVote).filter(
            EncryptedVote.receipt_hash == receipt_hash
        ).first()
        if not vote:
            raise HTTPException(status_code=404, detail="Receipt hash not found")
        vote_id = vote.vote_id

    if not vote_id and not entry_hash:
        raise HTTPException(status_code=400, detail="Provide vote_id, entry_hash, or receipt_hash")

    result = ledger_service.get_merkle_proof(db, election_id, vote_id=vote_id, entry_hash=entry_hash)
    if not result:
        raise HTTPException(status_code=404, detail="Entry not found or not yet committed")
    is_valid = ledger_service.verify_merkle_proof(
        result["entry_hash"], result["proof"], result["merkle_root"]
    )
    return MerkleProofResponse(
        entry_hash=result["entry_hash"],
        merkle_root=result["merkle_root"],
        proof=[MerkleProofStep(**step) for step in result["proof"]],
        valid=is_valid,
    )


@router.get("/pruning/history", response_model=List[PruningHistoryItem])
@limiter.limit("30/minute")
async def pruning_history(
    request: Request,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """US-46: Get pruning history for an election."""
    records = ledger_service.get_pruning_history(db, election_id)
    return [
        PruningHistoryItem(
            id=r.id,
            pruned_before_height=r.pruned_before_height,
            policy=r.policy,
            event_hash=r.event_hash,
            created_at=r.created_at,
        )
        for r in records
    ]


# ============================================================
# Write endpoints (authenticated, RBAC)
# ============================================================

@router.post("/submit")
async def submit_entry(
    election_id: Optional[uuid.UUID] = None,
    vote_id: Optional[uuid.UUID] = None,
    ciphertext: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "security_engineer"]))
):
    """Submit a new entry to the ledger. US-34: no plaintext stored."""
    try:
        entry = ledger_service.submit_entry(db, election_id, vote_id, ciphertext)
        return {
            "status": "submitted",
            "entry_hash": entry.entry_hash,
            "id": entry.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/propose")
async def propose_block(
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "security_engineer"]))
):
    """US-32 + US-33: Trigger block proposal (calling node must be active)."""
    try:
        block = ledger_service.propose_block(db, election_id)
        if not block:
            return {"status": "no_block_proposed"}
        return {
            "status": "proposed",
            "height": block.height,
            "block_hash": block.block_hash,
            "committed": block.committed,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve")
async def approve_block(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    node_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "security_engineer"]))
):
    """US-32 + US-43: Approve a block. Node must be active."""
    try:
        approval = ledger_service.approve_block(db, election_id, height,
                                                approving_node_id=node_id)
        return {
            "status": "approved",
            "node_id": approval.node_id,
            "height": approval.height,
            "block_hash": approval.block_hash,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/finalize")
async def finalize_block(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "security_engineer"]))
):
    """US-33 + US-44: Finalize block if quorum is met."""
    try:
        block = ledger_service.finalize_block(db, election_id, height)
        return {
            "status": "finalized",
            "height": block.height,
            "block_hash": block.block_hash,
            "commit_cert_hash": block.commit_cert_hash,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        detail = str(e)
        if "quorum_not_met" in detail:
            raise HTTPException(status_code=409, detail=detail)
        if "invalid_signature" in detail:
            raise HTTPException(status_code=422, detail=detail)
        if "split_brain" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


# US-32: Node management (admin only)
@router.post("/nodes/register", response_model=NodeDTO)
async def register_node(
    body: NodeRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """US-32: Register or re-activate a ledger node (admin only)."""
    try:
        node = ledger_service.register_node(db, body.node_id, body.public_key or "")
        return NodeDTO(
            node_id=node.node_id,
            public_key=node.public_key,
            is_active=node.is_active,
            created_at=node.created_at,
            last_seen=node.last_seen,
            last_height=node.last_height,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes/disable", response_model=NodeDTO)
async def disable_node(
    body: NodeDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """US-32: Disable a ledger node (admin only)."""
    try:
        node = ledger_service.disable_node(db, body.node_id)
        return NodeDTO(
            node_id=node.node_id,
            public_key=node.public_key,
            is_active=node.is_active,
            created_at=node.created_at,
            last_seen=node.last_seen,
            last_height=node.last_height,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/node/heartbeat")
async def node_heartbeat(
    body: HeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "security_engineer"]))
):
    """US-38: Record a node heartbeat (updates last_seen, last_height)."""
    try:
        node = ledger_service.record_heartbeat(db, body.node_id, body.last_height)
        return {
            "status": "ok",
            "node_id": node.node_id,
            "last_height": node.last_height,
            "last_seen": node.last_seen.isoformat() if node.last_seen else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/snapshot/create")
async def create_snapshot(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "auditor"]))
):
    """US-41: Create a chain snapshot."""
    try:
        snapshot = ledger_service.snapshot_create(db, election_id, height)
        return {
            "status": "created",
            "snapshot_hash": snapshot.snapshot_hash,
            "height": snapshot.height,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/snapshot/verify")
async def verify_snapshot(
    body: SnapshotVerifyRequest,
    db: Session = Depends(get_db)
):
    """US-41: Verify a snapshot hash against the stored snapshot."""
    return ledger_service.snapshot_verify(db, body.election_id, body.snapshot_hash)


@router.post("/prune")
async def prune_ledger(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """US-46: Prune old ciphertext_hash payloads. Hashes are always preserved."""
    try:
        record = ledger_service.prune(db, election_id, height)
        return {
            "status": "pruned",
            "pruned_before_height": record.pruned_before_height,
            "policy": record.policy,
            "event_hash": record.event_hash,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
