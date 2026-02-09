"""
Tallying Router for Epic 4

API endpoints that handle the vote tallying workflow:
- /start: Begins aggregation of encrypted votes
- /partial-decrypt: Accepts trustee decryption contributions  
- /finalize: Computes final results when enough trustees decrypt
- /status: Shows current tallying progress

All endpoints require a valid election ID and proper
authorization (trustees only for decrypt operations).

Author: Kapil (Epic 4)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from datetime import datetime
from app.models.database import get_db, Election, EncryptedVote, PartialDecryption, TallyingSession
from app.models.schemas import (
    TallyStartRequest,
    TallyStartResponse,
    PartialDecryptRequest,
    PartialDecryptResponse,
    TallyFinalizeRequest,
    TallyFinalizeResponse,
    TallyStatusResponse
)
from app.services import tallying_service
from app.utils.auth_utils import require_roles
from app.models.auth_models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start", response_model=TallyStartResponse)
def start_tallying(
    request: TallyStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """
    Start the tallying process for an election
    
    - **election_id**: UUID of the election to tally
    
    This endpoint:
    1. Retrieves all encrypted votes
    2. Aggregates them using homomorphic encryption
    3. Creates a tallying session
    4. Waits for trustees to perform partial decryption
    """
    logger.info(f"Received tally start request for election: {request.election_id}")
    
    try:
        result = tallying_service.start_tallying(
            db=db,
            election_id=str(request.election_id)
        )
        
        return TallyStartResponse(
            session_id=result["session_id"],
            election_id=request.election_id,
            status=result["status"],
            message="Tallying started successfully. Waiting for trustees to decrypt.",
            total_votes=result["total_votes"],
            required_trustees=result["required_trustees"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tally start failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tallying failed: {str(e)}"
        )


@router.post("/partial-decrypt/{trustee_id}", response_model=PartialDecryptResponse)
def partial_decrypt(
    trustee_id: UUID,
    election_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["trustee"]))
):
    """
    Perform partial decryption by a trustee
    
    - **trustee_id**: UUID of the trustee performing decryption
    - **election_id**: UUID of the election (query parameter)
    
    Each trustee must call this endpoint to contribute their partial decryption.
    Once enough trustees (threshold) have decrypted, results can be finalized.
    """
    logger.info(f"Trustee {trustee_id} performing partial decryption for election {election_id}")
    
    try:
        if current_user.trustee_vote_limit is not None and current_user.trustee_votes_verified >= current_user.trustee_vote_limit:
            raise HTTPException(status_code=403, detail="Trustee verification limit reached")

        result = tallying_service.partial_decrypt(
            db=db,
            election_id=str(election_id),
            trustee_id=str(trustee_id)
        )
        
        message = f"Partial decryption successful. Progress: {result['completed_trustees']}/{result['required_trustees']}"
        if result["can_finalize"]:
            message += " - Ready to finalize!"
        
        current_user.trustee_votes_verified = (current_user.trustee_votes_verified or 0) + 1
        db.commit()

        return PartialDecryptResponse(
            decryption_id=result["decryption_id"],
            election_id=election_id,
            trustee_id=trustee_id,
            status="success",
            message=message,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Partial decryption failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Partial decryption failed: {str(e)}"
        )


@router.post("/finalize", response_model=TallyFinalizeResponse)
def finalize_tally(
    request: TallyFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """
    Finalize the tally and compute final results
    
    - **election_id**: UUID of the election
    
    This endpoint:
    1. Verifies that enough trustees have performed partial decryption
    2. Combines partial decryptions using threshold cryptography
    3. Computes final vote counts
    4. Generates verification hash
    5. Stores final results
    """
    logger.info(f"Finalizing tally for election: {request.election_id}")
    
    try:
        result = tallying_service.finalize_tally(
            db=db,
            election_id=str(request.election_id)
        )
        
        return TallyFinalizeResponse(
            result_id=result["result_id"],
            election_id=request.election_id,
            final_tally=result["final_tally"],
            total_votes_tallied=result["total_votes_tallied"],
            verification_hash=result["verification_hash"],
            message="Tally finalized successfully. Results are now public."
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tally finalization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finalization failed: {str(e)}"
        )


@router.get("/status/{election_id}", response_model=TallyStatusResponse)
def get_tally_status(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the status of an ongoing tallying process
    
    - **election_id**: UUID of the election
    """
    session = db.query(TallyingSession).filter(
        TallyingSession.election_id == election_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tallying session not found"
        )
    
    return TallyStatusResponse(
        session_id=session.session_id,
        election_id=session.election_id,
        status=session.status,
        required_trustees=session.required_trustees,
        completed_trustees=session.completed_trustees,
        started_at=session.started_at,
        completed_at=session.completed_at
    )


@router.get("/aggregate-info/{election_id}")
def get_aggregation_info(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get information about vote aggregation for an election
    
    - **election_id**: UUID of the election
    """
    from app.models import EncryptedVote
    from datetime import datetime
    
    session = db.query(TallyingSession).filter(
        TallyingSession.election_id == election_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tallying session not found"
        )
    
    votes = db.query(EncryptedVote).filter(
        EncryptedVote.election_id == election_id
    ).all()
    
    return {
        "election_id": election_id,
        "total_votes": len(votes),
        "aggregated": session.aggregated_ciphertext is not None,
        "aggregation_size_bytes": len(session.aggregated_ciphertext) if session.aggregated_ciphertext else 0,
        "session_status": session.status,
        "timestamp": datetime.utcnow()
    }


# Import datetime at module level
from datetime import datetime
