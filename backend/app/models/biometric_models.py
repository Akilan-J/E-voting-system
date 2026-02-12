"""
Biometric Authentication Models
Supports fingerprint, Face ID, Windows Hello via WebAuthn
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class BiometricCredential(Base):
    """
    Store WebAuthn credentials for biometric authentication
    Supports: Fingerprint, Face ID, Windows Hello, Security Keys
    """
    __tablename__ = "biometric_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    credential_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    # WebAuthn credential data
    credential_public_key = Column(Text, nullable=False)  # Public key for verification
    credential_raw_id = Column(String(255), unique=True, nullable=False)  # Unique credential ID
    
    # Device/authenticator info
    authenticator_type = Column(String(50))  # 'platform' (built-in) or 'cross-platform' (USB key)
    device_name = Column(String(255))  # User-friendly name: "iPhone 13", "Windows Hello", etc.
    
    # Metadata
    counter = Column(Integer, default=0)  # Signature counter for replay protection
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    # Backup authentication (optional)
    backup_eligible = Column(Boolean, default=False)  # Can be backed up to cloud
    backup_state = Column(Boolean, default=False)  # Currently backed up
