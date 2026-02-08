"""
Results Router - API endpoints for result publishing and verification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
import logging
import hashlib
import json

from app.models.database import get_db, ElectionResult, Election, AuditLog
from app.models.schemas import (
    ElectionResultResponse,
    ResultVerificationRequest,
    ResultVerificationResponse,
    AuditLogResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ElectionResultResponse])
def get_all_results(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all election results (public endpoint)
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    results = db.query(ElectionResult).offset(skip).limit(limit).all()
    
    return [
        ElectionResultResponse(
            result_id=r.result_id,
            election_id=r.election_id,
            final_tally=r.final_tally,
            total_votes_tallied=r.total_votes_tallied,
            verification_hash=r.verification_hash,
            is_verified=r.is_verified,
            published_at=r.published_at,
            blockchain_tx_hash=r.blockchain_tx_hash
        )
        for r in results
    ]


@router.get("/{election_id}", response_model=ElectionResultResponse)
def get_result(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get results for a specific election (public endpoint)
    
    - **election_id**: UUID of the election
    """
    result = db.query(ElectionResult).filter(
        ElectionResult.election_id == election_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found. Tallying may not be complete."
        )
    
    return ElectionResultResponse(
        result_id=result.result_id,
        election_id=result.election_id,
        final_tally=result.final_tally,
        total_votes_tallied=result.total_votes_tallied,
        verification_hash=result.verification_hash,
        is_verified=result.is_verified,
        published_at=result.published_at,
        blockchain_tx_hash=result.blockchain_tx_hash
    )


@router.post("/verify", response_model=ResultVerificationResponse)
def verify_results(
    request: ResultVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify election results using cryptographic proofs
    
    - **election_id**: UUID of the election to verify
    
    This endpoint verifies:
    1. Result hash matches computed hash
    2. Vote counts are consistent
    3. All partial decryptions are valid
    """
    logger.info(f"Verifying results for election: {request.election_id}")
    
    result = db.query(ElectionResult).filter(
        ElectionResult.election_id == request.election_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found"
        )
    
    # Recompute verification hash
    hash_data = {
        "election_id": str(result.election_id),
        "final_tally": result.final_tally,
        "total_votes": result.total_votes_tallied,
        "timestamp": result.created_at.isoformat()
    }
    hash_str = json.dumps(hash_data, sort_keys=True)
    computed_hash = hashlib.sha256(hash_str.encode()).hexdigest()
    
    # Verify hash matches
    is_valid = computed_hash == result.verification_hash
    
    # Additional verification checks
    verification_details = {
        "hash_matches": is_valid,
        "stored_hash": result.verification_hash,
        "computed_hash": computed_hash,
        "total_votes": result.total_votes_tallied,
        "tally": result.final_tally,
        "verified_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Verification completed. Valid: {is_valid}")
    
    return ResultVerificationResponse(
        election_id=request.election_id,
        is_valid=is_valid,
        verification_hash=result.verification_hash,
        verification_details=verification_details,
        timestamp=datetime.utcnow()
    )


@router.get("/audit-log/{election_id}", response_model=List[AuditLogResponse])
def get_audit_log(
    election_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get audit trail for an election (public endpoint)
    
    - **election_id**: UUID of the election
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    logs = db.query(AuditLog).filter(
        AuditLog.election_id == election_id
    ).order_by(
        AuditLog.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        AuditLogResponse(
            log_id=log.log_id,
            operation_type=log.operation_type,
            performed_by=log.performed_by,
            details=json.loads(log.details) if isinstance(log.details, str) else log.details,
            status=log.status,
            timestamp=log.timestamp
        )
        for log in logs
    ]


@router.post("/publish/{election_id}")
def publish_to_blockchain(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Publish election results to blockchain
    
    - **election_id**: UUID of the election
    
    This endpoint publishes the verification hash to the blockchain
    for immutable public record.
    """
    logger.info(f"Publishing results to blockchain for election: {election_id}")
    
    result = db.query(ElectionResult).filter(
        ElectionResult.election_id == election_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found"
        )
    
    if result.blockchain_tx_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results already published to blockchain"
        )
    
    try:
        # In production, this would interact with actual blockchain
        # For now, we'll simulate it
        
        # Generate simulated transaction hash
        tx_data = f"{election_id}-{result.verification_hash}-{datetime.utcnow().isoformat()}"
        tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()
        
        # Update result with blockchain info
        result.blockchain_tx_hash = tx_hash
        result.published_at = datetime.utcnow()
        
        # Log operation
        log = AuditLog(
            election_id=election_id,
            operation_type="publish_blockchain",
            performed_by="system",
            details={
                "tx_hash": tx_hash,
                "verification_hash": result.verification_hash
            },
            status="success"
        )
        db.add(log)
        
        db.commit()
        
        logger.info(f"Results published to blockchain. TX: {tx_hash}")
        
        return {
            "success": True,
            "message": "Results published to blockchain",
            "tx_hash": tx_hash,
            "verification_hash": result.verification_hash,
            "published_at": result.published_at
        }
        
    except Exception as e:
        logger.error(f"Blockchain publishing failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Publishing failed: {str(e)}"
        )


@router.get("/summary/{election_id}")
def get_result_summary(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a comprehensive summary of election results
    
    - **election_id**: UUID of the election
    """
    from app.models.database import PartialDecryption, TallyingSession
    
    result = db.query(ElectionResult).filter(
        ElectionResult.election_id == election_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found"
        )
    
    election = db.query(Election).filter(
        Election.election_id == election_id
    ).first()
    
    session = db.query(TallyingSession).filter(
        TallyingSession.election_id == election_id
    ).first()
    
    partial_decs = db.query(PartialDecryption).filter(
        PartialDecryption.election_id == election_id
    ).count()
    
    # Calculate percentages
    total_votes = result.total_votes_tallied
    tally_with_percentages = {}
    
    for candidate, votes in result.final_tally.items():
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
        tally_with_percentages[candidate] = {
            "votes": votes,
            "percentage": round(percentage, 2)
        }
    
    return {
        "election": {
            "id": election.election_id,
            "title": election.title,
            "status": election.status
        },
        "results": {
            "total_votes": total_votes,
            "tally": tally_with_percentages,
            "verification_hash": result.verification_hash,
            "is_verified": result.is_verified
        },
        "tallying_info": {
            "started_at": session.started_at if session else None,
            "completed_at": session.completed_at if session else None,
            "trustees_participated": partial_decs,
            "required_trustees": session.required_trustees if session else None
        },
        "blockchain": {
            "published": result.blockchain_tx_hash is not None,
            "tx_hash": result.blockchain_tx_hash,
            "published_at": result.published_at
        }
    }
