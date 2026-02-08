"""
Trustees Router - API endpoints for trustee management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from app.models.database import get_db, Trustee
from app.models.schemas import (
    TrusteeCreate,
    TrusteeResponse,
    KeyShareGenerateRequest,
    KeyShareGenerateResponse,
    SuccessResponse
)
from app.services import threshold_crypto_service, encryption_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=TrusteeResponse, status_code=status.HTTP_201_CREATED)
def register_trustee(
    trustee: TrusteeCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new trustee
    
    - **name**: Trustee name
    - **email**: Trustee email (unique)
    """
    logger.info(f"Registering new trustee: {trustee.email}")
    
    # Check if email already exists
    existing = db.query(Trustee).filter(Trustee.email == trustee.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create trustee
    db_trustee = Trustee(
        name=trustee.name,
        email=trustee.email,
        status="active"
    )
    
    db.add(db_trustee)
    db.commit()
    db.refresh(db_trustee)
    
    logger.info(f"Trustee registered successfully: {db_trustee.trustee_id}")
    
    return TrusteeResponse(
        id=db_trustee.id,
        trustee_id=db_trustee.trustee_id,
        name=db_trustee.name,
        email=db_trustee.email,
        status=db_trustee.status,
        created_at=db_trustee.created_at,
        has_key_share=db_trustee.key_share_encrypted is not None
    )


@router.get("", response_model=List[TrusteeResponse])
def list_trustees(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all registered trustees
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    trustees = db.query(Trustee).offset(skip).limit(limit).all()
    
    return [
        TrusteeResponse(
            id=t.id,
            trustee_id=t.trustee_id,
            name=t.name,
            email=t.email,
            status=t.status,
            created_at=t.created_at,
            has_key_share=t.key_share_encrypted is not None
        )
        for t in trustees
    ]


@router.get("/{trustee_id}", response_model=TrusteeResponse)
def get_trustee(
    trustee_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get trustee details by ID
    
    - **trustee_id**: UUID of the trustee
    """
    trustee = db.query(Trustee).filter(Trustee.trustee_id == trustee_id).first()
    
    if not trustee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trustee not found"
        )
    
    return TrusteeResponse(
        id=trustee.id,
        trustee_id=trustee.trustee_id,
        name=trustee.name,
        email=trustee.email,
        status=trustee.status,
        created_at=trustee.created_at,
        has_key_share=trustee.key_share_encrypted is not None
    )


@router.post("/{trustee_id}/key-share", response_model=KeyShareGenerateResponse)
def generate_key_share(
    trustee_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate and assign key share to a trustee
    
    - **trustee_id**: UUID of the trustee
    """
    logger.info(f"Generating key share for trustee: {trustee_id}")
    
    trustee = db.query(Trustee).filter(Trustee.trustee_id == trustee_id).first()
    
    if not trustee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trustee not found"
        )
    
    try:
        # Generate keypair for the trustee
        public_key, private_key = encryption_service.generate_keypair()
        
        # In production, private_key would be split using threshold crypto
        # For now, we'll store it directly (encrypted in practice)
        shares = threshold_crypto_service.split_secret(private_key)
        
        # Find this trustee's share
        trustee_share = None
        for share in shares:
            if share["trustee_index"] == trustee.id:
                trustee_share = share["share_data"]
                break
        
        if not trustee_share:
            # Use first share as fallback
            trustee_share = shares[0]["share_data"]
        
        # Store public key and key share
        trustee.public_key = public_key
        trustee.key_share_encrypted = trustee_share
        
        db.commit()
        
        logger.info(f"Key share generated for trustee: {trustee_id}")
        
        return KeyShareGenerateResponse(
            trustee_id=trustee.trustee_id,
            public_key=public_key,
            message="Key share generated successfully"
        )
        
    except Exception as e:
        logger.error(f"Key share generation failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key share generation failed: {str(e)}"
        )


@router.delete("/{trustee_id}", response_model=SuccessResponse)
def delete_trustee(
    trustee_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a trustee (mark as inactive)
    
    - **trustee_id**: UUID of the trustee
    """
    trustee = db.query(Trustee).filter(Trustee.trustee_id == trustee_id).first()
    
    if not trustee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trustee not found"
        )
    
    # Mark as inactive instead of deleting
    trustee.status = "inactive"
    db.commit()
    
    logger.info(f"Trustee marked as inactive: {trustee_id}")
    
    return SuccessResponse(
        success=True,
        message="Trustee marked as inactive"
    )


@router.get("/threshold/info")
async def get_threshold_info():
    """
    Get threshold cryptography configuration
    """
    return threshold_crypto_service.get_threshold_info()
