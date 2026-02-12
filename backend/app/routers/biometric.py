from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import os
import json
import base64
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    RegistrationCredential,
    AuthenticationCredential,
)

from app.models.database import get_db
from app.models.auth_models import User, SecurityLog
from app.models.biometric_models import BiometricCredential
from app.utils.auth_utils import get_current_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.auth_schemas import Token

router = APIRouter()

RP_ID = os.getenv("RP_ID", "localhost")
RP_NAME = "E-Voting System"
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

# In-memory store for challenges (In production, use Redis)
registration_challenges = {}
authentication_challenges = {}

@router.get("/register/options")
async def get_registration_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Generate registration options for the client to start biometric enrollment
    """
    # Check if user already has a credential (optional, can allow multiple)
    existing_credentials = db.query(BiometricCredential).filter(
        BiometricCredential.user_id == current_user.user_id
    ).all()
    
    exclude_credentials = [
        {"id": base64url_to_bytes(c.credential_raw_id), "type": "public-key"}
        for c in existing_credentials
    ]

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(current_user.user_id).encode("utf-8"),
        user_name=current_user.identity_hash[:16],
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,  # Prefer fingerprint/face scan
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=exclude_credentials,
    )

    # Store challenge for verification step
    registration_challenges[str(current_user.user_id)] = options.challenge
    
    return json.loads(options_to_json(options))

@router.post("/register/verify")
async def verify_registration(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Verify the registration response from the client and save the credential
    """
    body = await request.json()
    challenge = registration_challenges.get(str(current_user.user_id))
    
    if not challenge:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")

    try:
        verification = verify_registration_response(
            credential=body,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {str(e)}")

    # Clear challenge
    del registration_challenges[str(current_user.user_id)]

    # Save credential to DB
    new_cred = BiometricCredential(
        user_id=current_user.user_id,
        credential_public_key=base64.b64encode(verification.credential_public_key).decode("utf-8"),
        credential_raw_id=body["id"],
        authenticator_type="platform",
        device_name="Biometric Authenticator",
        counter=verification.sign_count
    )
    
    db.add(new_cred)
    
    # Also update user state if needed
    current_user.mfa_enabled = True
    
    db.commit()

    return {"status": "success", "message": "Biometric authentication registered successfully"}

@router.get("/authenticate/options/{user_id}")
async def get_authentication_options(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Step 1: Generate authentication options for the client to start biometric login
    """
    # Find user and their credentials
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    credentials = db.query(BiometricCredential).filter(
        BiometricCredential.user_id == user_id
    ).all()
    
    if not credentials:
        raise HTTPException(status_code=400, detail="No biometric credentials found for this user")

    allow_credentials = [
        {"id": base64url_to_bytes(c.credential_raw_id), "type": "public-key"}
        for c in credentials
    ]

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    # Store challenge for verification
    authentication_challenges[str(user_id)] = options.challenge
    
    return json.loads(options_to_json(options))

@router.post("/authenticate/verify/{user_id}", response_model=Token)
async def verify_authentication(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2: Verify the authentication response and issue a full session token
    """
    body = await request.json()
    challenge = authentication_challenges.get(str(user_id))
    
    if not challenge:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")

    user = db.query(User).filter(User.user_id == user_id).first()
    credential_record = db.query(BiometricCredential).filter(
        BiometricCredential.credential_raw_id == body["id"]
    ).first()
    
    if not credential_record:
        raise HTTPException(status_code=404, detail="Credential record not found")

    try:
        verification = verify_authentication_response(
            credential=body,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64.b64decode(credential_record.credential_public_key),
            credential_current_sign_count=credential_record.counter,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication verification failed: {str(e)}")

    # Clear challenge
    del authentication_challenges[str(user_id)]

    # Update counter
    credential_record.counter = verification.new_sign_count
    credential_record.last_used = datetime.utcnow()
    db.commit()

    # Issue full token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Audit Log
    log = SecurityLog(
        user_id=user.user_id,
        event_type="BIOMETRIC_LOGIN",
        details="Biometric authentication successful"
    )
    db.add(log)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "mfa_required": False}
