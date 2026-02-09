"""
Mock Data Router - Generate test data for development
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import random
from typing import Optional
import json
from datetime import datetime, timedelta

start_time = datetime.utcnow()
end_time = start_time + timedelta(days=1)
from datetime import datetime, timedelta

start_time = datetime.utcnow()
end_time = start_time + timedelta(days=1)


from app.models.database import get_db, Election, EncryptedVote, Trustee
from app.models.schemas import MockVotesGenerateRequest, MockVotesGenerateResponse
from app.services import encryption_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-votes", response_model=MockVotesGenerateResponse)
def generate_mock_votes(
    count: int = 100,
    election_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Generate mock encrypted votes for testing
    
    - **count**: Number of votes to generate (1-10000)
    - **election_id**: UUID of election (optional, uses first active election if not provided)
    
    This endpoint generates random encrypted votes with realistic distribution
    for testing the tallying system without requiring actual voters.
    """
    logger.info(f"Generating {count} mock votes")
    
    if count < 1 or count > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Count must be between 1 and 10000"
        )
    
    # Get election
    if election_id:
        election = db.query(Election).filter(Election.election_id == election_id).first()
    else:
        election = db.query(Election).filter(Election.status.in_(["active", "pending"])).first()
    
    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active election found"
        )
    
    logger.info(f"Generating votes for election: {election.title}")
    
    try:
        # Parse candidates
        candidates = election.candidates if isinstance(election.candidates, list) else json.loads(election.candidates)
        if not isinstance(candidates, list) or not candidates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Election has no candidates configured"
            )
        num_candidates = len(candidates)
        candidate_ids = [c.get("id", index + 1) for index, c in enumerate(candidates)]
        
        # Generate or load encryption keys
        if not election.encryption_params:
            public_key, private_key = encryption_service.generate_keypair()
            election.encryption_params = {
                "public_key": public_key,
                "private_key": private_key  # In production, this would be split among trustees
            }
            db.commit()
        else:
            public_key = election.encryption_params["public_key"]
        
        # Load public key
        encryption_service.load_public_key(public_key)
        
        # Generate votes with realistic distribution
        distribution = {}
        votes_generated = 0
        
        for i in range(count):
            # Random candidate selection (weighted random for realism)
            # Give first candidate slight advantage for interesting results
            weights = [0.35] + [0.65 / (num_candidates - 1)] * (num_candidates - 1) if num_candidates > 1 else [1.0]
            candidate_id = random.choices(candidate_ids, weights=weights, k=1)[0]
            
            # Track distribution
            candidate_index = candidate_ids.index(candidate_id)
            candidate_name = candidates[candidate_index].get("name", f"Candidate {candidate_id}")
            distribution[candidate_name] = distribution.get(candidate_name, 0) + 1
            
            # Encrypt vote
            encrypted_vote = encryption_service.encrypt_vote(candidate_id, num_candidates)
            
            # Generate unique nonce
            nonce = f"mock-{election.election_id}-{i}-{random.randint(1000, 9999)}"
            
            # Store encrypted vote
            vote = EncryptedVote(
                election_id=election.election_id,
                encrypted_vote=encrypted_vote,
                vote_proof=f"mock_proof_{i}",
                nonce=nonce,
                is_tallied=False
            )
            db.add(vote)
            
            # EPIC 3: Ledger Hook
            # Submit to ledger
            try:
                from app.services.ledger_service import ledger_service
                ledger_service.submit_entry(
                    db, 
                    election_id=election.election_id,
                    vote_id=None, # Vote ID not available until commit/refresh usually, or we assume sync? 
                    # Actually keeping vote_id null as per request "vote_id nullable" or referenced.
                    # Ideally we want the vote UUID. hash(nonce) is in encrypted_vote?
                    # vote object doesn't have ID until flush?
                    # The vote object has defaults in DB but not in python obj until flush?
                    # Actually `vote_id` is a column default=uuid4, but sqlalchemy doesn't generate it python side unless specified.
                    # We should generate vote_id in python to link it?
                    # Existing code: `vote = EncryptedVote(...)`. It does NOT set vote_id. 
                    # So Postgres generates it. We can't know it unless we flush.
                    ciphertext=encrypted_vote
                )
            except Exception as e:
                logger.error(f"Ledger submission failed: {e}")

            votes_generated += 1
            
            # Commit in batches for performance
            if (i + 1) % 100 == 0:
                db.commit()
                logger.info(f"Generated {i + 1}/{count} votes...")
        
        # Final commit
        db.commit()
        
        # Update election total voters
        election.total_voters += votes_generated
        db.commit()
        
        logger.info(f"Successfully generated {votes_generated} mock votes")
        logger.info(f"Distribution: {distribution}")
        
        return MockVotesGenerateResponse(
            message=f"Generated {votes_generated} mock votes successfully",
            election_id=election.election_id,
            votes_generated=votes_generated,
            distribution=distribution
        )
        
    except Exception as e:
        logger.error(f"Mock vote generation failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vote generation failed: {str(e)}"
        )


@router.post("/reset-database")
def reset_database(
    confirm: bool = False,
    db: Session = Depends(get_db)
):
    """
    Reset database to initial state (development only)
    
    - **confirm**: Must be true to execute (safety check)
    
    ⚠️ WARNING: This deletes all data except trustees and elections!
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to reset database"
        )
    
    logger.warning("Resetting database...")
    
    try:
        from app.models import (
            EncryptedVote, PartialDecryption, ElectionResult,
            AuditLog, VerificationProof, TallyingSession
        )
        from app.models.auth_models import SecurityLog, BlindToken
        
        # Delete all data
        db.query(VerificationProof).delete()
        db.query(AuditLog).delete()
        db.query(ElectionResult).delete()
        db.query(PartialDecryption).delete()
        db.query(EncryptedVote).delete()
        db.query(TallyingSession).delete()
        db.query(SecurityLog).delete()
        db.query(BlindToken).delete()
        
        # Reset election statuses
        db.query(Election).update({"status": "active", "total_voters": 0})
        
        db.commit()
        
        logger.info("Database reset successfully")
        
        return {
            "success": True,
            "message": "Database reset successfully",
            "note": "Elections and trustees preserved; tokens and security logs cleared"
        }
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


@router.get("/election-stats")
def get_election_stats(
    election_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Get statistics about an election
    
    - **election_id**: UUID of election (optional, uses first active if not provided)
    """
    from app.models import PartialDecryption, TallyingSession
    
    if election_id:
        election = db.query(Election).filter(Election.election_id == election_id).first()
    else:
        election = db.query(Election).first()
    
    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Election not found"
        )
    
    votes_count = db.query(EncryptedVote).filter(
        EncryptedVote.election_id == election.election_id
    ).count()
    
    tallied_votes = db.query(EncryptedVote).filter(
        EncryptedVote.election_id == election.election_id,
        EncryptedVote.is_tallied == True
    ).count()
    
    partial_decs = db.query(PartialDecryption).filter(
        PartialDecryption.election_id == election.election_id
    ).count()
    
    session = db.query(TallyingSession).filter(
        TallyingSession.election_id == election.election_id
    ).first()
    
    candidates = election.candidates if isinstance(election.candidates, list) else json.loads(election.candidates)
    
    return {
        "election": {
            "id": election.election_id,
            "title": election.title,
            "status": election.status,
            "candidates": candidates
        },
        "votes": {
            "total": votes_count,
            "tallied": tallied_votes,
            "untallied": votes_count - tallied_votes
        },
        "tallying": {
            "started": session is not None,
            "status": session.status if session else None,
            "trustees_completed": partial_decs,
            "required_trustees": session.required_trustees if session else None
        }
    }


@router.get("/citizens")
def get_citizens(db: Session = Depends(get_db)):
    """
    View the citizen source-of-truth database.
    Shows the mapping of credential hashes to eligibility.
    """
    from app.models import Citizen
    citizens = db.query(Citizen).all()
    return citizens


@router.post("/setup-system")
def setup_system(
    db: Session = Depends(get_db)
):
    """
    Complete system initialization:
    1. Create default election if none exists
    2. Populate Citizen database (source of truth)
    3. Setup Trustees for threshold cryptography
    4. Setup Admin and Trustee Users (US-6 RBAC)
    """
    from app.models.database import Election
    from app.models.auth_models import Citizen, User
    import hashlib
    
    # ... (Election creation logic remains) ...
    # 1. Ensure Election exists
    election = db.query(Election).first()
    if not election:
        election = Election(
            title="General Election 2026",
            description="Secure, multi-trustee e-voting demonstration",
            candidates=[
                {"id": 1, "name": "Alice Johnson", "party": "Progressive"},
                {"id": 2, "name": "Bob Smith", "party": "Conservative"},
                {"id": 3, "name": "Charlie Davis", "party": "Independent"}
            ],
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(), # Demo ends immediately
            status="active"
        )
        db.add(election)
        db.commit()
    
    # 2. Populate Citizen Database
    test_credentials = ["123456789012", "987654321098", "555566667777"]
    citizens_added = 0
    for cred in test_credentials:
        ident_hash = hashlib.sha256(cred.encode()).hexdigest()
        if not db.query(Citizen).filter(Citizen.identity_hash == ident_hash).first():
            db.add(Citizen(
                identity_hash=ident_hash,
                full_name_hashed=hashlib.sha256(f"Citizen {cred}".encode()).hexdigest(),
                is_eligible_voter=True
            ))
            citizens_added += 1
            
    # 2.5 Setup ADMIN and TRUSTEE users for RBAC
    # Admin
    admin_cred = "admin123"
    admin_hash = hashlib.sha256(admin_cred.encode()).hexdigest()
    if not db.query(User).filter(User.identity_hash == admin_hash).first():
        db.add(User(identity_hash=admin_hash, role="admin"))
        citizens_added += 1 # Counting users added too
        
    # Trustees (trustee1..5)
    for i in range(1, 6):
        t_cred = f"trustee{i}"
        t_hash = hashlib.sha256(t_cred.encode()).hexdigest()
        if not db.query(User).filter(User.identity_hash == t_hash).first():
            db.add(User(identity_hash=t_hash, role="trustee"))
            citizens_added += 1

    # 3. Setup Trustees (Crypto Keys)
    trustees_result = setup_test_trustees(db)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"System initialized. Added voters, admin (admin123), and trustees (trustee1-5).",
        "trustees": trustees_result
    }

@router.post("/setup-trustees")
def setup_test_trustees(
    db: Session = Depends(get_db)
):
    """
    Ensure default trustees exist and have key shares
    
    This endpoint is idempotent - it won't create duplicates
    """
    logger.info("Setting up test trustees...")
    
    # Get active election
    election = db.query(Election).first()
    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No election found. Initialize database first."
        )
    
    # Get all trustees
    trustees = db.query(Trustee).all()
    
    if len(trustees) < 5:
        return {
            "success": False,
            "message": "Not enough trustees. Run database initialization first.",
            "trustees_found": len(trustees)
        }
    
    # Generate keypair for election if not exists
    if not election.encryption_params:
        public_key, private_key = encryption_service.generate_keypair()
        election.encryption_params = {
            "public_key": public_key,
            "private_key": private_key
        }
        logger.info("Generated new keypair for election")
    else:
        public_key = election.encryption_params["public_key"]
        private_key = election.encryption_params["private_key"]
        logger.info("Using existing election keypair")
    
    # Split private key into shares for trustees
    trustees_updated = 0
    from app.services import threshold_crypto_service
    shares = threshold_crypto_service.split_secret(private_key)
    
    for trustee in trustees[:5]:  # Only first 5
        try:
            # Find matching share for this trustee
            for share in shares:
                if share["trustee_index"] == trustee.id:
                    trustee.public_key = public_key
                    trustee.key_share_encrypted = share["share_data"]
                    trustees_updated += 1
                    break
        except Exception as e:
            logger.error(f"Failed to setup trustee {trustee.id}: {e}")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Setup {trustees_updated} trustees with key shares from election keypair",
        "total_trustees": len(trustees),
        "ready_for_tallying": trustees_updated >= 3
    }


@router.post("/generate-zk-proof")
def generate_mock_zk_proof(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate a valid Mock ZK Proof Bundle for a completed election.
    Useful for testing US-63 without full cryptographic implementation.
    """
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
        
    from app.models.ledger_models import LedgerEntry
    from app.models.database import ElectionResult
    from app.utils.crypto_utils import MerkleTree
    import hashlib

    result = db.query(ElectionResult).filter(ElectionResult.election_id == election_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Election results not published")

    entries = db.query(LedgerEntry).filter(LedgerEntry.election_id == election_id).order_by(LedgerEntry.created_at).all()
    leaves = [e.entry_hash for e in entries]
    ledger_root = MerkleTree(leaves).get_root() if leaves else "0" * 64

    proof_hash = hashlib.sha256(
        f"{election_id}|{result.verification_hash}|{ledger_root}".encode()
    ).hexdigest()

    return {
        "election_id": election_id,
        "proof_bundle": {
            "election_id": str(election_id),
            "verification_hash": result.verification_hash,
            "ledger_root": ledger_root,
            "proof_hash": proof_hash,
            "method": "hash-linked-proof"
        }
    }
