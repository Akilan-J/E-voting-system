"""
Database models and connection
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from datetime import datetime, timedelta

start_time = datetime.utcnow()
end_time = start_time + timedelta(days=1)

import os
import uuid

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('POSTGRES_USER', 'admin')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'secure_password')}@"
    f"{os.getenv('POSTGRES_HOST', '127.0.0.1')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'evoting')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database Models
class Trustee(Base):
    __tablename__ = "trustees"

    id = Column(Integer, primary_key=True, index=True)
    trustee_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    public_key = Column(Text)
    key_share_encrypted = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    partial_decryptions = relationship("PartialDecryption", back_populates="trustee")


class Election(Base):
    __tablename__ = "elections"

    id = Column(Integer, primary_key=True, index=True)
    election_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(50), default="pending")
    total_voters = Column(Integer, default=0)
    candidates = Column(JSON, nullable=False)
    encryption_params = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    encrypted_votes = relationship("EncryptedVote", back_populates="election")
    partial_decryptions = relationship("PartialDecryption", back_populates="election")
    result = relationship("ElectionResult", back_populates="election", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="election")
    tallying_session = relationship("TallyingSession", back_populates="election", uselist=False)


class EncryptedVote(Base):
    __tablename__ = "encrypted_votes"

    id = Column(Integer, primary_key=True, index=True)
    vote_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"))
    encrypted_vote = Column(Text, nullable=False)
    vote_proof = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_tallied = Column(Boolean, default=False)
    nonce = Column(String(255), unique=True)

    election = relationship("Election", back_populates="encrypted_votes")


class PartialDecryption(Base):
    __tablename__ = "partial_decryptions"

    id = Column(Integer, primary_key=True, index=True)
    decryption_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"))
    trustee_id = Column(UUID(as_uuid=True), ForeignKey("trustees.trustee_id", ondelete="CASCADE"))
    partial_result = Column(Text, nullable=False)
    decryption_proof = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)

    election = relationship("Election", back_populates="partial_decryptions")
    trustee = relationship("Trustee", back_populates="partial_decryptions")


class ElectionResult(Base):
    __tablename__ = "election_results"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"), unique=True)
    final_tally = Column(JSON, nullable=False)
    total_votes_tallied = Column(Integer, nullable=False)
    verification_hash = Column(String(255))
    blockchain_tx_hash = Column(String(255))
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)

    election = relationship("Election", back_populates="result")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"))
    operation_type = Column(String(100), nullable=False)
    performed_by = Column(String(255))
    details = Column(JSON)
    status = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Validation & Inmutability
    previous_hash = Column(String(64), nullable=True) # SHA256 of previous log
    current_hash = Column(String(64), unique=True, nullable=True) # SHA256 of this log

    election = relationship("Election", back_populates="audit_logs")


class VerificationProof(Base):
    __tablename__ = "verification_proofs"

    id = Column(Integer, primary_key=True, index=True)
    proof_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"))
    proof_type = Column(String(100), nullable=False)
    proof_data = Column(Text, nullable=False)
    is_valid = Column(Boolean)
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class TallyingSession(Base):
    __tablename__ = "tallying_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    election_id = Column(UUID(as_uuid=True), ForeignKey("elections.election_id", ondelete="CASCADE"), unique=True)
    status = Column(String(50), default="initiated")
    aggregated_ciphertext = Column(Text)
    required_trustees = Column(Integer, nullable=False)
    completed_trustees = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    election = relationship("Election", back_populates="tallying_session")
