from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.models.database import get_db, AuditLog
from app.models.auth_models import User, SecurityLog, EligibilityRecord
from app.schemas.auth_schemas import EligibilityResponse, BlindSignRequest, BlindSignResponse
from app.utils.auth_utils import get_current_user
from app.utils.crypto_utils import sign_blinded_message

router = APIRouter()

@router.get("/eligibility/{election_id}", response_model=EligibilityResponse)
async def check_eligibility(
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
async def issue_credential(
    req: BlindSignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify Eligibility
    # Re-use logic or call function
    if current_user.role != "voter" or not current_user.is_active:
        raise HTTPException(status_code=403, detail="Not eligible")

    # 2. Check if already issued (De-duplication US-6/US-13 context)
    # We check SecurityLog for previous issuance
    existing_issuance = db.query(SecurityLog).filter(
        SecurityLog.user_id == current_user.user_id,
        SecurityLog.event_type == "CREDENTIAL_ISSUED",
        SecurityLog.details.contains(str(req.election_id))
    ).first()
    
    if existing_issuance:
        raise HTTPException(status_code=400, detail="Credential already issued for this election")

    # 3. Sign
    try:
        blinded_int = int(req.blinded_payload)
        # Sign using the isolated signer utility
        signature_int = sign_blinded_message(blinded_int)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload format (must be integer string)")

    # 4. Log issuance (Internal - for duplicate prevention)
    sec_log = SecurityLog(
        user_id=current_user.user_id,
        event_type="CREDENTIAL_ISSUED",
        details=f"Election: {req.election_id}"
    )
    db.add(sec_log)

    # 5. Log audit event (Public - US-4: No join key)
    # This proves a credential was issued, but doesn't say to whom (User ID is not here).
    audit_log = AuditLog(
        election_id=req.election_id,
        operation_type="CREDENTIAL_ISSUED",
        status="SUCCESS",
        timestamp=datetime.utcnow(),
        details={"info": "Blind credential issued"} 
        # CAUTION: Do NOT log the signature or blinded token if it can be linked back by the user later in a way that reveals identity to the auditor.
        # US-4 says "Record credential issuance event to audit log".
    )
    db.add(audit_log)
    
    db.commit()
    
    return {"signature": str(signature_int)}
