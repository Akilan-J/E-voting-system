from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import json
from functools import lru_cache
import pyotp
import hashlib
import logging
import os


logger = logging.getLogger(__name__)

from app.models.database import get_db
from app.models.auth_models import User, SecurityLog
from app.schemas.auth_schemas import (
    LoginRequest, Token, MFASetupResponse, MFAVerifyRequest, UserResponse, RoleUpdateRequest
)
from app.utils.auth_utils import (
    create_access_token, get_current_user, get_current_admin, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.utils.auth import RateLimiter
from typing import List
from uuid import UUID

router = APIRouter()

HARD_CODED_CREDENTIALS_PATH = os.getenv(
    "HARD_CODED_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "..", "config", "hardcoded_credentials.json")
)


@lru_cache(maxsize=1)
def load_role_credentials() -> dict:
    try:
        with open(HARD_CODED_CREDENTIALS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        logger.error("Hardcoded credentials file missing: %s", HARD_CODED_CREDENTIALS_PATH)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hardcoded credentials file missing"
        ) from exc
    except json.JSONDecodeError as exc:
        logger.error("Hardcoded credentials file invalid JSON: %s", HARD_CODED_CREDENTIALS_PATH)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hardcoded credentials file invalid"
        ) from exc

    if not isinstance(data, dict):
        logger.error("Hardcoded credentials file must be a JSON object")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hardcoded credentials file invalid"
        )

    return {str(key): str(value) for key, value in data.items()}

def hash_identity(credential: str) -> str:
    # US-1: "Map verified claims to eligibility lookup key (hashed)"
    # Simple SHA256 hash of the credential (e.g. National ID) with optional salt
    salt = os.getenv("IDENTITY_SALT", "")
    return hashlib.sha256(f"{salt}{credential}".encode()).hexdigest()

@router.post("/login", response_model=Token)
def login(
    login_req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=10, seconds=60))
):
    from app.models.auth_models import Citizen
    role_credentials = load_role_credentials()
    salted_hash = hash_identity(login_req.credential)
    unsalted_hash = hashlib.sha256(login_req.credential.encode()).hexdigest()
    identity_hashes = [salted_hash]
    if unsalted_hash not in identity_hashes:
        identity_hashes.append(unsalted_hash)

    hardcoded_login = login_req.credential in role_credentials

    if hardcoded_login:
        forced_role = role_credentials[login_req.credential]
        user = db.query(User).filter(User.identity_hash.in_(identity_hashes)).first()
        if not user:
            user = User(identity_hash=salted_hash, role=forced_role)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if user.role != forced_role:
                user.role = forced_role
                db.commit()
        citizen = None
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials"
        )
    
    # 0. Check for privileged accounts (Admin/Trustee) first
    if not hardcoded_login:
        user = db.query(User).filter(User.identity_hash.in_(identity_hashes)).first()
        if user and user.role in ["admin", "trustee", "auditor", "security_engineer"]:
            # Privileged users don't need to be in Citizen DB for this demo/system
            pass
        else:
            # 1. For Voters: Check the Citizen source of truth (e.g. Aadhaar)
            citizen = db.query(Citizen).filter(Citizen.identity_hash.in_(identity_hashes)).first()
            
            if not citizen:
                # Log failed attempt
                logger.warning(f"Unauthorized login attempt with credential hash: {salted_hash[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Credential not found in national citizen database"
                )
        
    # If not a privileged user, check eligibility
    if not user:
        if not citizen.is_eligible_voter or citizen.is_deceased:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Citizen exists but is not eligible to vote (Inactive or Deceased)"
            )

    # 1.5 Risk Analysis
    from app.core.security_core import SecurityRiskAnalyzer, RiskLevel, ImmutableLogger
    client_ip = request.client.host if request.client else "127.0.0.1"
    # No user_id yet if login fails, but we use identity_hash?
    # Or just track IP risk.
    risk = SecurityRiskAnalyzer.calculate_risk(client_ip, "unknown", db)
    if risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
         ImmutableLogger.log(db, None, "LOGIN_BLOCKED", "SYSTEM", {"risk": risk.value, "ip": client_ip}, "BLOCKED", client_ip)
         raise HTTPException(status_code=403, detail="Login blocked due to high risk assessment")

    # 2. Check if local user account exists, if not create it from Citizen data
    if not user:
        user = db.query(User).filter(User.identity_hash.in_(identity_hashes)).first()

    if not user:
        # Map citizen to a local voter account
        user = User(identity_hash=salted_hash, role="voter")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log account provisioning
        log = SecurityLog(
            user_id=user.user_id,
            event_type="USER_CREATED",
            details="Voter account provisioned from Citizen record"
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

@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(User.created_at.desc()).all()

@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    update: RoleUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    allowed_roles = {"voter", "admin", "trustee", "auditor", "security_engineer"}
    if update.role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = update.role
    if update.role == "trustee":
        user.trustee_vote_limit = update.trustee_vote_limit if update.trustee_vote_limit is not None else 100
        if user.trustee_votes_verified is None:
            user.trustee_votes_verified = 0
    else:
        user.trustee_vote_limit = None
        user.trustee_votes_verified = 0

    db.commit()
    db.refresh(user)

    log = SecurityLog(
        user_id=current_user.user_id,
        event_type="ROLE_UPDATED",
        details=f"Updated user {user.user_id} role to {user.role}"
    )
    db.add(log)
    db.commit()
    return user

@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
def verify_mfa_setup(
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
    
    # 1. If completing setup (first-time enable):
    if not current_user.mfa_enabled:
        current_user.mfa_enabled = True
        db.commit()
        # Issue a full token so the frontend stays authenticated after setup
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(current_user.user_id), "role": current_user.role},
            expires_delta=access_token_expires
        )
        log = SecurityLog(
            user_id=current_user.user_id,
            event_type="MFA_SETUP_COMPLETE",
            details="MFA Enabled and verified"
        )
        db.add(log)
        db.commit()
        return {"access_token": access_token, "token_type": "bearer", "role": current_user.role, "message": "MFA Enabled"}
    
    # 2. MFA login verification — user authenticated with mfa_pending token
    # Issue full token with real role
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.user_id), "role": current_user.role},
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
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
