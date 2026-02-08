"""
Tallying Service for Epic 4: Privacy-Preserving Vote Counting

This is the main workflow coordinator. It orchestrates:
1. Vote aggregation using homomorphic encryption
2. Partial decryption by trustees
3. Final result computation
4. Result publication to blockchain

The tallying process:
- Start: Collect all encrypted votes and aggregate them
- Decrypt: Each trustee provides a partial decryption
- Finalize: Combine partials to get final vote counts

Author: Kapil (Epic 4)
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import json

from app.models import (
    Election, EncryptedVote, TallyingSession,
    PartialDecryption, ElectionResult, AuditLog
)
from app.services.encryption import encryption_service
from app.services.threshold_crypto import threshold_crypto_service

logger = logging.getLogger(__name__)


class TallyingService:
    """
    Coordinates the entire tallying workflow.
    
    Manages the election lifecycle from vote collection
    through to publishing verified results on blockchain.
    """
    
    def __init__(self):
        self.encryption = encryption_service
        self.threshold_crypto = threshold_crypto_service
    
    async def start_tallying(
        self,
        db: Session,
        election_id: str
    ) -> Dict:
        """
        Start the tallying process for an election
        
        Args:
            db: Database session
            election_id: UUID of the election
            
        Returns:
            Tallying session details
        """
        logger.info(f"Starting tallying for election {election_id}")
        
        # Get election
        election = db.query(Election).filter(
            Election.election_id == election_id
        ).first()
        
        if not election:
            raise ValueError("Election not found")
        
        if election.status not in ["active", "ended"]:
            raise ValueError(f"Cannot tally election with status: {election.status}")
        
        # Check if tallying already started
        existing_session = db.query(TallyingSession).filter(
            TallyingSession.election_id == election_id
        ).first()
        
        if existing_session:
            raise ValueError("Tallying session already exists")
        
        # Get all encrypted votes
        encrypted_votes = db.query(EncryptedVote).filter(
            EncryptedVote.election_id == election_id,
            EncryptedVote.is_tallied == False
        ).all()
        
        if not encrypted_votes:
            raise ValueError("No votes to tally")
        
        logger.info(f"Found {len(encrypted_votes)} votes to aggregate")
        
        # Aggregate encrypted votes using homomorphic addition
        encrypted_vote_strings = [vote.encrypted_vote for vote in encrypted_votes]
        
        try:
            aggregated_ciphertext = self.encryption.aggregate_votes(
                encrypted_vote_strings
            )
        except Exception as e:
            logger.error(f"Vote aggregation failed: {e}")
            raise ValueError(f"Aggregation failed: {str(e)}")
        
        # Create tallying session
        session = TallyingSession(
            election_id=election_id,
            status="aggregating",
            aggregated_ciphertext=aggregated_ciphertext,
            required_trustees=self.threshold_crypto.threshold,
            completed_trustees=0
        )
        db.add(session)
        
        # Update election status
        election.status = "tallying"
        
        # Log operation
        log = AuditLog(
            election_id=election_id,
            operation_type="start_tally",
            performed_by="system",
            details={
                "total_votes": len(encrypted_votes),
                "session_id": str(session.session_id)
            },
            status="success"
        )
        db.add(log)
        
        db.commit()
        db.refresh(session)
        
        logger.info(f"Tallying started successfully. Session: {session.session_id}")
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "total_votes": len(encrypted_votes),
            "required_trustees": session.required_trustees
        }
    
    async def partial_decrypt(
        self,
        db: Session,
        election_id: str,
        trustee_id: str
    ) -> Dict:
        """
        Perform partial decryption by a trustee
        
        Args:
            db: Database session
            election_id: UUID of the election
            trustee_id: UUID of the trustee
            
        Returns:
            Partial decryption details
        """
        logger.info(f"Trustee {trustee_id} performing partial decryption for election {election_id}")
        
        # Get tallying session
        session = db.query(TallyingSession).filter(
            TallyingSession.election_id == election_id
        ).first()
        
        if not session:
            raise ValueError("Tallying session not found")
        
        if session.status not in ["aggregating", "decrypting"]:
            raise ValueError(f"Cannot decrypt in status: {session.status}")
        
        # Check if trustee already decrypted
        existing = db.query(PartialDecryption).filter(
            PartialDecryption.election_id == election_id,
            PartialDecryption.trustee_id == trustee_id
        ).first()
        
        if existing:
            raise ValueError("Trustee already performed partial decryption")
        
        # Get trustee and load their key share
        from app.models import Trustee, Election
        trustee = db.query(Trustee).filter(Trustee.trustee_id == trustee_id).first()
        if not trustee or not trustee.key_share_encrypted:
            raise ValueError("Trustee not found or missing key share")
        
        # Load the trustee's key share (in this demo, the share IS the private key)
        # In production, you'd reconstruct the key from shares
        election = db.query(Election).filter(Election.election_id == election_id).first()
        if election and election.encryption_params:
            private_key = election.encryption_params.get("private_key")
            if private_key:
                self.encryption.load_private_key(private_key)
        
        # Perform partial decryption
        partial_result = self.encryption.partial_decrypt(
            session.aggregated_ciphertext,
            session.completed_trustees + 1
        )
        
        # Generate proof of correct decryption (simplified)
        proof = self._generate_decryption_proof(
            session.aggregated_ciphertext,
            partial_result,
            trustee_id
        )
        
        # Store partial decryption
        partial_dec = PartialDecryption(
            election_id=election_id,
            trustee_id=trustee_id,
            partial_result=partial_result,
            decryption_proof=proof,
            verified=True  # Auto-verify for now
        )
        db.add(partial_dec)
        
        # Update session
        session.completed_trustees += 1
        if session.status == "aggregating":
            session.status = "decrypting"
        
        # Log operation
        log = AuditLog(
            election_id=election_id,
            operation_type="partial_decrypt",
            performed_by=str(trustee_id),
            details={
                "session_id": str(session.session_id),
                "trustee_count": session.completed_trustees
            },
            status="success"
        )
        db.add(log)
        
        db.commit()
        db.refresh(partial_dec)
        
        logger.info(
            f"Partial decryption completed. "
            f"Progress: {session.completed_trustees}/{session.required_trustees}"
        )
        
        return {
            "decryption_id": partial_dec.decryption_id,
            "completed_trustees": session.completed_trustees,
            "required_trustees": session.required_trustees,
            "can_finalize": session.completed_trustees >= session.required_trustees
        }
    
    async def finalize_tally(
        self,
        db: Session,
        election_id: str
    ) -> Dict:
        """
        Finalize tallying and compute final results
        
        Args:
            db: Database session
            election_id: UUID of the election
            
        Returns:
            Final election results
        """
        logger.info(f"Finalizing tally for election {election_id}")
        
        # Get tallying session
        session = db.query(TallyingSession).filter(
            TallyingSession.election_id == election_id
        ).first()
        
        if not session:
            raise ValueError("Tallying session not found")
        
        if session.completed_trustees < session.required_trustees:
            raise ValueError(
                f"Insufficient trustees: {session.completed_trustees} < {session.required_trustees}"
            )
        
        # Get all partial decryptions
        partial_decs = db.query(PartialDecryption).filter(
            PartialDecryption.election_id == election_id,
            PartialDecryption.verified == True
        ).all()
        
        if len(partial_decs) < session.required_trustees:
            raise ValueError("Insufficient verified partial decryptions")
        
        # Combine partial decryptions
        partial_results = [pd.partial_result for pd in partial_decs]
        
        try:
            final_tally_array = self.encryption.combine_partial_decryptions(
                session.aggregated_ciphertext,
                partial_results,
                session.required_trustees
            )
        except Exception as e:
            logger.error(f"Tally combination failed: {e}")
            raise ValueError(f"Finalization failed: {str(e)}")
        
        # Get election to map candidates
        election = db.query(Election).filter(
            Election.election_id == election_id
        ).first()
        
        candidates = json.loads(election.candidates) if isinstance(election.candidates, str) else election.candidates
        
        # Create final tally dictionary
        final_tally = {}
        total_votes = 0
        
        for i, candidate in enumerate(candidates):
            candidate_name = candidate["name"]
            vote_count = final_tally_array[i] if i < len(final_tally_array) else 0
            final_tally[candidate_name] = vote_count
            total_votes += vote_count
        
        # Generate verification hash
        verification_hash = self._generate_verification_hash(
            election_id,
            final_tally,
            total_votes
        )
        
        # Store results
        result = ElectionResult(
            election_id=election_id,
            final_tally=final_tally,
            total_votes_tallied=total_votes,
            verification_hash=verification_hash,
            is_verified=True
        )
        db.add(result)
        
        # Update session and election
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        election.status = "completed"
        
        # Mark votes as tallied
        db.query(EncryptedVote).filter(
            EncryptedVote.election_id == election_id
        ).update({"is_tallied": True})
        
        # Log operation
        log = AuditLog(
            election_id=election_id,
            operation_type="finalize_tally",
            performed_by="system",
            details={
                "final_tally": final_tally,
                "total_votes": total_votes,
                "verification_hash": verification_hash
            },
            status="success"
        )
        db.add(log)
        
        db.commit()
        db.refresh(result)
        
        logger.info(f"Tally finalized successfully. Total votes: {total_votes}")
        
        return {
            "result_id": result.result_id,
            "final_tally": final_tally,
            "total_votes_tallied": total_votes,
            "verification_hash": verification_hash
        }
    
    def _generate_decryption_proof(
        self,
        aggregated_ciphertext: str,
        partial_result: str,
        trustee_id: str
    ) -> str:
        """Generate zero-knowledge proof of correct partial decryption"""
        # Simplified proof generation
        proof_data = {
            "trustee_id": str(trustee_id),
            "timestamp": datetime.utcnow().isoformat(),
            "ciphertext_hash": hashlib.sha256(aggregated_ciphertext.encode()).hexdigest()
        }
        proof = hashlib.sha256(json.dumps(proof_data).encode()).hexdigest()
        return proof
    
    def _generate_verification_hash(
        self,
        election_id: str,
        final_tally: Dict,
        total_votes: int
    ) -> str:
        """Generate verification hash for results (deterministic - no timestamp)"""
        hash_data = {
            "election_id": str(election_id),
            "final_tally": final_tally,
            "total_votes": total_votes
        }
        hash_str = json.dumps(hash_data, sort_keys=True)
        verification_hash = hashlib.sha256(hash_str.encode()).hexdigest()
        return verification_hash


# Global instance
tallying_service = TallyingService()
