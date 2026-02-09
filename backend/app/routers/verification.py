
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import hashlib
import json
import logging

from app.models import get_db, EncryptedVote, ElectionResult
from app.models.ledger_models import LedgerEntry
from app.models.schemas import (
    ReceiptVerificationRequest, 
    ReceiptVerificationResponse,
    ZKProofVerificationRequest,
    ZKProofVerificationResponse
)
from app.utils.crypto_utils import MerkleTree
from app.utils.auth import RateLimiter

router = APIRouter()
logger = logging.getLogger(__name__)

# US-62: Receipt Verification Logic
@router.post("/receipt", response_model=ReceiptVerificationResponse)
async def verify_receipt(
    request: ReceiptVerificationRequest,
    db: Session = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=10, seconds=60))
):
    """
    Verify if a receipt hash exists in the ledger and checks its inclusion.
    """
    logger.info(f"Verifying receipt: {request.receipt_hash}")
    
    # 1. Fetch ledger entries to build the tree
    entries = db.query(LedgerEntry).filter(LedgerEntry.election_id == request.election_id).order_by(LedgerEntry.created_at).all()

    found_entry = None
    leaves = []
    target_index = -1
    
    # 2. Build Leaves and Find Target
    for index, entry in enumerate(entries):
        current_hash = entry.entry_hash
        leaves.append(current_hash)
        if current_hash == request.receipt_hash:
            found_entry = entry
            target_index = index

    if not found_entry or target_index == -1:
        return ReceiptVerificationResponse(
            receipt_hash=request.receipt_hash,
            status="not_found"
        )
        
    # 3. Generate Real Merkle Proof
    tree = MerkleTree(leaves)
    proof_siblings = tree.get_proof(target_index)
    root_hash = tree.get_root()
    
    return ReceiptVerificationResponse(
        receipt_hash=request.receipt_hash,
        status="verified",
        block_index=target_index,
        timestamp=found_entry.created_at,
        proof={
            "root": root_hash,
            "siblings": proof_siblings,
            "index": target_index
        }
    )

# US-63: ZK Proof Verification Logic
@router.post("/zk-proof", response_model=ZKProofVerificationResponse)
async def verify_zk_proof(
    request: ZKProofVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify a Zero-Knowledge Proof bundle using independent crypto logic.
    """
    # 1. Fetch public election artifacts (commitment, public keys)
    result = db.query(ElectionResult).filter(ElectionResult.election_id == request.election_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Election results not published")
        
    start_time = datetime.now()
    
    proof = request.proof_bundle
    required_keys = {"election_id", "verification_hash", "ledger_root", "proof_hash"}
    if not required_keys.issubset(set(proof.keys())):
        raise HTTPException(status_code=400, detail="Invalid proof bundle format")

    # Compute ledger merkle root
    entries = db.query(LedgerEntry).filter(LedgerEntry.election_id == request.election_id).order_by(LedgerEntry.created_at).all()
    leaves = [e.entry_hash for e in entries]
    merkle_root = MerkleTree(leaves).get_root() if leaves else "0" * 64

    expected_proof_hash = hashlib.sha256(
        f"{proof['election_id']}|{proof['verification_hash']}|{proof['ledger_root']}".encode()
    ).hexdigest()

    is_valid = (
        str(proof["election_id"]) == str(request.election_id)
        and proof["verification_hash"] == result.verification_hash
        and proof["ledger_root"] == merkle_root
        and proof["proof_hash"] == expected_proof_hash
    )

    evidence_hash = hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
    verification_duration = (datetime.now() - start_time).total_seconds() * 1000

    return ZKProofVerificationResponse(
        is_valid=is_valid,
        verification_time_ms=verification_duration,
        evidence_hash=evidence_hash,
        details={
            "ledger_root_match": proof["ledger_root"] == merkle_root,
            "verification_hash_match": proof["verification_hash"] == result.verification_hash,
            "proof_hash_match": proof["proof_hash"] == expected_proof_hash
        }
    )
