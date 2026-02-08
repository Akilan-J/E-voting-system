from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.models.database import get_db, AuditLog
from app.models.auth_models import User, SecurityLog, EligibilityRecord
from app.schemas.auth_schemas import (
    EligibilityResponse, BlindSignRequest, BlindSignResponse, 
    VoteCastRequest, VoteCastResponse
)
from app.utils.auth_utils import get_current_user
# from app.utils.crypto_utils import sign_blinded_message # Deprecated by BlindSigner

router = APIRouter()

@router.get("/eligibility/{election_id}", response_model=EligibilityResponse)
def check_eligibility(
    election_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if explicit eligibility record exists
    record = db.query(EligibilityRecord).filter(
        EligibilityRecord.identity_hash == current_user.identity_hash,
        EligibilityRecord.election_id == election_id
    ).first()
    
    if record:
        return {
            "is_eligible": record.is_eligible,
            "reason_code": record.reason_code,
            "election_id": election_id
        }
        
    # Default logic: Active voters are eligible
    if current_user.role == "voter" and current_user.is_active:
        return {
            "is_eligible": True,
            "reason_code": "ACTIVE_VOTER",
            "election_id": election_id
        }
    
    return {
        "is_eligible": False,
        "reason_code": "NOT_FOUND",
        "election_id": election_id
    }

@router.post("/credential/issue", response_model=BlindSignResponse)
def issue_credential(
    req: BlindSignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.database import Election
    from app.core.security_core import BlindSigner, ImmutableLogger, SecurityRiskAnalyzer, RiskLevel
    
    # 0. Risk Analysis (IP/Geo)
    client_ip = "127.0.0.1" # In prod: request.client.host
    risk = SecurityRiskAnalyzer.calculate_risk(client_ip, str(current_user.user_id), db)
    if risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
        # Log anomaly
        ImmutableLogger.log(db, str(req.election_id), "RISK_BLOCK", "SYSTEM", {"risk": risk.value, "user": str(current_user.user_id)}, "BLOCKED", client_ip)
        raise HTTPException(status_code=403, detail="High risk access detected. Please contact support.")

    # 1. Check if election exists
    election = db.query(Election).filter(Election.election_id == req.election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    # 2. Verify Eligibility & RBAC
    if current_user.role != "voter" or not current_user.is_active:
        raise HTTPException(status_code=403, detail="User is not an active voter")

    # 3. Check for Duplicate Issuance (US-6/US-13)
    # Strict 1-person-1-credential check using SecurityLog
    search_str = f"Election: {req.election_id}"
    existing_issuance = db.query(SecurityLog).filter(
        SecurityLog.user_id == current_user.user_id,
        SecurityLog.event_type == "CREDENTIAL_ISSUED",
        SecurityLog.details.contains(str(req.election_id))
    ).first()
    
    if existing_issuance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Credential has already been issued to this identity for election {req.election_id}"
        )

    # 4. Sign (Blind Signature Protocol)
    try:
        blinded_int = int(req.blinded_payload)
        # Sign using the isolated KeyManager via BlindSigner
        signature_int = BlindSigner.sign_blinded_int(blinded_int)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    # 5. Log issuance (Internal - Link Identity to Election for Deduplication)
    sec_log = SecurityLog(
        user_id=current_user.user_id,
        event_type="CREDENTIAL_ISSUED",
        details=f"Election: {req.election_id} - Issued at {datetime.utcnow()}"
    )
    db.add(sec_log)

    # 6. Log audit event (Public - Immutable Hash Chain)
    # US-4: Record credential issuance event to audit log. No PII.
    ImmutableLogger.log(
        db=db,
        election_id=str(req.election_id),
        operation="CREDENTIAL_ISSUED",
        actor="ISSUER_SERVICE",
        details={"info": "Blind credential issued", "timestamp": str(datetime.utcnow())},
        status="SUCCESS",
        ip=client_ip
    )
    
    db.commit()
    
    return {"signature": str(signature_int)}

@router.post("/vote", response_model=VoteCastResponse)
def cast_vote(
    req: VoteCastRequest,
    db: Session = Depends(get_db)
):
    """
    US-3: Vote Verification using Unblinded Credential.
    US-4: Credential Lifecycle (Expiry, Reuse).
    """
    from app.models.auth_models import BlindToken
    from app.core.security_core import BlindSigner, ImmutableLogger
    from app.services.ledger_service import ledger_service
    import hashlib
    
    # 1. Verify Signature
    try:
        token_int = int(req.token)
        sig_int = int(req.signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token/signature format (must be int)")

    if not BlindSigner.verify_token_signature(token_int, sig_int):
         raise HTTPException(status_code=403, detail="Invalid Credential Signature")

    # 2. Decode Token and Validate Structure (US-4)
    # Token message structure: "election_id|expiry_timestamp|nonce"
    try:
        # Simple decode simulation: In reality we would decode bytes
        # Here we assume the token IS the hash of the structure (simplified for demo because passing massive int is hard without byte encoding lib usage)
        # BUT the prompt requires "Token format".
        # Let's assume the token_int passed IS the message.
        # We need to trust the client sent a valid structure? No, we verify signature.
        # If signature is valid, WE (the server) signed it.
        # If we signed it, it must have been valid at issuance?
        # NO. We blind signed it. We didn't see it.
        # So we must check the content NOW.
        # Constraint: We can't recover string from int easily if not standard encoding.
        # I'll assume the client ensures `token` is `int.from_bytes(payload.encode(), 'big')`
        
        token_bytes = token_int.to_bytes((token_int.bit_length() + 7) // 8, byteorder='big')
        payload_str = token_bytes.decode('utf-8')
        parts = payload_str.split("|")
        
        if len(parts) != 3:
             raise HTTPException(status_code=403, detail="Invalid token structure")
             
        t_election_id, t_expiry, t_nonce = parts
        
        # 3. Check Election Binding
        if str(t_election_id) != str(req.election_id):
             raise HTTPException(status_code=403, detail="Token not bound to this election")
             
        # 4. Check Expiry
        # t_expiry is unix timestamp
        if float(t_expiry) < datetime.utcnow().timestamp():
             raise HTTPException(status_code=403, detail="Credential expired")
             
    except Exception as e:
         # If we can't parse what we signed, it's garbage.
         # But wait, we signed a blinded hash usually.
         # For this implementation to work as described (blind->sign->unblind), the user unblinds the signature on the *message hash* or *message*.
         # RSA blind signature works on the message int directly.
         # So unblinded `s` satisfies `s^e = m`. `m` is the integer.
         # So we successfully recovered `m`.
         # So `e` logic above is sound.
         raise HTTPException(status_code=403, detail=f"Invalid credential payload: {str(e)}")

    # 5. Check Token Reuse (Double Voting)
    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    
    # 5a. Atomic Check-and-Set (Database constraint on unique token_hash)
    existing_token = db.query(BlindToken).filter(BlindToken.token_hash == token_hash).first()
    
    if existing_token:
        # Check status
        if existing_token.status == "REVOKED":
             raise HTTPException(status_code=403, detail="Credential Revoked")
        raise HTTPException(status_code=403, detail="Double Voting Detected")
        
    # 6. Record Token Usage
    new_token_record = BlindToken(
        token_hash=token_hash,
        status="USED",
        election_id=req.election_id,
        expiry=datetime.fromtimestamp(float(t_expiry)),
        used_at=datetime.utcnow()
    )
    db.add(new_token_record)
    
    # 7. Submit to Ledger
    try:
        from app.models.database import EncryptedVote
        import uuid
        
        vote_id = uuid.uuid4()
        nonce = str(uuid.uuid4()) # In prod: Client should provide this for verification, or we generate securely
        
        # Store actual vote payload (Ledger stores hash)
        enc_vote = EncryptedVote(
            vote_id=vote_id,
            election_id=req.election_id,
            encrypted_vote=req.vote_ciphertext,
            nonce=nonce,
            timestamp=datetime.utcnow(),
            is_tallied=False
        )
        db.add(enc_vote)
        db.flush() # Ensure it's ready for FKs if any
        
        entry = ledger_service.submit_entry(db, req.election_id, vote_id, req.vote_ciphertext)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ledger submission failed: {str(e)}")
        
    # 8. Audit Log
    ImmutableLogger.log(
        db=db,
        election_id=str(req.election_id),
        operation="VOTE_CAST",
        actor="ANONYMOUS",
        details={"ledger_entry": entry.entry_hash},
        status="SUCCESS",
        ip="127.0.0.1" # In prod: request.client.host
    )
    
    db.commit()
    
    return {
        "status": "VOTE_ACCEPTED",
        "receipt_hash": entry.entry_hash,
        "timestamp": datetime.utcnow()
    }