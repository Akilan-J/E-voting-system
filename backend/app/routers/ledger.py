"""Epic 3: Immutable Vote Ledger - API Router

Exposes REST endpoints for blockchain operations:
- Read: /blocks, /proof, /verify-chain
- Write: /submit, /propose, /approve, /finalize
- Maintenance: /snapshot, /prune, /node/health
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os

from app.models.database import get_db
from app.models.blockchain import BlockHeader, LedgerEntryDTO
from app.services.ledger_service import ledger_service
from app.models.ledger_models import LedgerBlock

# US-45: Rate limiting and caching
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# Initialize rate limiter
enable_rate_limiting = os.getenv("LEDGER_ENABLE_RATE_LIMITING", "true").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=enable_rate_limiting)

router = APIRouter()

@router.get("/blocks", response_model=List[BlockHeader])
@limiter.limit("100/minute")  # US-45: Rate limiting for public access
async def list_blocks(
    request: Request,  # Required for rate limiter
    election_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List blocks from the ledger (US-45: rate-limited public endpoint)"""
    query = db.query(LedgerBlock)
    if election_id:
        query = query.filter(LedgerBlock.election_id == election_id)
        
    blocks = query.filter(LedgerBlock.committed == True).order_by(LedgerBlock.height.asc()).limit(limit).all()
    
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

@router.post("/submit")
async def submit_entry(
    election_id: Optional[uuid.UUID] = None,
    vote_id: Optional[uuid.UUID] = None,
    ciphertext: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Submit a new entry to the ledger"""
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
    db: Session = Depends(get_db)
):
    """Trigger block proposal (Manual/Cron)"""
    try:
        block = ledger_service.propose_block(db, election_id)
        if not block:
             return {"status": "no_block_proposed"}
        return {
            "status": "proposed",
            "height": block.height,
            "block_hash": block.block_hash
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve")
async def approve_block(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """Approve a block as the current node"""
    try:
        approval = ledger_service.approve_block(db, election_id, height)
        return {
            "status": "approved",
            "node_id": approval.node_id,
            "signature": approval.signature
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/finalize")
async def finalize_block(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """Finalize block if quorum met"""
    try:
        block = ledger_service.finalize_block(db, election_id, height)
        return {
            "status": "finalized",
            "height": block.height,
            "commit_cert_hash": block.commit_cert_hash
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/verify-chain")
async def verify_chain(
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """Verify chain integrity"""
    return ledger_service.verify_chain(db, election_id)

@router.post("/snapshot/create")
async def create_snapshot(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """Create a chain snapshot"""
    try:
        snapshot = ledger_service.snapshot_create(db, election_id, height)
        return {
            "status": "created",
            "snapshot_hash": snapshot.snapshot_hash,
            "height": snapshot.height
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/prune")
async def prune_ledger(
    height: int,
    election_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    """Prune old ledger payloads"""
    try:
        record = ledger_service.prune(db, election_id, height)
        return {
            "status": "pruned",
            "policy": record.policy,
            "event_hash": record.event_hash
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

