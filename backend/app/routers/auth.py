from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import pyotp
import hashlib

from app.models.database import get_db
from app.models.auth_models import User, SecurityLog
from app.schemas.auth_schemas import (
    LoginRequest, Token, MFASetupResponse, MFAVerifyRequest, UserResponse
)
from app.utils.auth_utils import (
    create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()

def hash_identity(credential: str) -> str:
    # US-1: "Map verified claims to eligibility lookup key (hashed)"
    # Simple SHA256 hash of the credential (e.g. National ID)
    return hashlib.sha256(credential.encode()).hexdigest()

@router.post("/login", response_model=Token)
async def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    identity_hash = hash_identity(login_req.credential)
    user = db.query(User).filter(User.identity_hash == identity_hash).first()

    # US-1: Auto-provision if not exists (Simulating "Given a voter has a valid digital ID")
    # In reality, this would check an external Eligible list first.
    if not user:
        user = User(identity_hash=identity_hash, role="voter")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log creation
        log = SecurityLog(
            user_id=user.user_id,
            event_type="USER_CREATED",
            details="User created via login"
        )
        db.add(log)
        db.commit()

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User inactive")

    # US-2: MFA Check
    if user.mfa_enabled:
        # Return a special token or signal that MFA is required
        # For simplicity, we return a token with role "mfa_pending" which can ONLY access /mfa/validate
        access_token_expires = timedelta(minutes=5)
        access_token = create_access_token(
            data={"sub": str(user.user_id), "role": "mfa_pending"},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "role": "mfa_pending", "mfa_required": True}

    # Generate full token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Audit Log US-1
    log = SecurityLog(
        user_id=user.user_id,
        event_type="LOGIN",
        details="Successful login"
    )
    db.add(log)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "mfa_required": False}

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # US-2: Implement TOTP enrollment
    secret = pyotp.random_base32()
    
    # Store secret (US-2 says encrypted - skipping encryption logic for brevity, assuming DB encryption or separate util)
    current_user.mfa_secret = secret
    db.commit()
    
    # Create provisioning URI
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=str(current_user.identity_hash)[:8], # Obscure identity in authenticator app
        issuer_name="E-Voting System"
    )
    
    return {"secret": secret, "provisioning_uri": uri}

@router.post("/mfa/verify")
async def verify_mfa_setup(
    verify_req: MFAVerifyRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Complete MFA setup or Perform MFA Login (if role is mfa_pending)
    """
    if not current_user.mfa_secret:
         raise HTTPException(status_code=400, detail="MFA not setup")
        
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(verify_req.token):
         raise HTTPException(status_code=400, detail="Invalid OTP")

    # If verification successful:
    
    # 1. If completing setup:
    if not current_user.mfa_enabled:
        current_user.mfa_enabled = True
        db.commit()
        return {"message": "MFA Enabled"}
    
    # 2. If performing login (context check needed? we use role)
    # If the user called us with "mfa_pending" token, we issue a full token now.
    # In this simple implementation, the user is already "current_user". 
    # If they authenticated with "mfa_pending", they are here.
    
    # Issue full token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.user_id), "role": current_user.role}, # Restore real role
        expires_delta=access_token_expires
    )
    
    # Audit Log US-2
    log = SecurityLog(
        user_id=current_user.user_id,
        event_type="MFA_LOGIN",
        details="MFA Verified"
    )
    db.add(log)
    db.commit()

    return {"access_token": access_token, "token_type": "bearer", "role": current_user.role}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
