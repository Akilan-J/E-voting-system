
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import io
import zipfile
import json
import logging

from app.models import get_db, Election, ElectionResult, EncryptedVote, Trustee, Incident, AuditLog
from app.models.schemas import IncidentResponse, IncidentCreate, IncidentUpdate
from app.services.monitoring import logging_service
from app.utils.crypto_utils import signer
from app.services.ledger_service import ledger_service
from app.utils.auth import RoleChecker

router = APIRouter()
logger = logging.getLogger(__name__)

# US-65: Transparency Dashboard
@router.get("/dashboard/{election_id}")
async def get_dashboard_metrics(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get aggregate metrics for the transparency dashboard.
    Safe for public consumption (no PII).
    """
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
        
    # Aggregate metrics
    total_votes = db.query(EncryptedVote).filter(EncryptedVote.election_id == election_id).count()
    
    # Calculate votes over time (last 24h buckets)
    # Simplified: just getting a count for now. Real implementation would groupby timestamp.
    
    trustees_count = db.query(Trustee).count() # Global or per election? Schema is global currently.
    
    logging_service.log_event("dashboard_view", "INFO", {"election_id": str(election_id)})
    
    return {
        "election_status": election.status,
        "total_voters_registered": election.total_voters,
        "votes_cast_current": total_votes,
        "turnout_percentage": (total_votes / election.total_voters * 100) if election.total_voters > 0 else 0,
        "trustees_active": trustees_count,
        "last_updated": datetime.utcnow()
    }

# US-66: Evidence Package
@router.get("/evidence/{election_id}")
async def get_evidence_package(
    election_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate and download a zip file containing public election artifacts.
    """
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    result = db.query(ElectionResult).filter(ElectionResult.election_id == election_id).first()
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Manifest
        manifest = {
            "election_id": str(election.election_id),
            "title": election.title,
            "candidates": election.candidates,
            "generated_at": datetime.utcnow().isoformat()
        }
        manifest_str = json.dumps(manifest, indent=2)
        zip_file.writestr("manifest.json", manifest_str)
        
        # 1.1 Sign Manifest (US-66)
        signature = signer.sign_data(manifest)
        zip_file.writestr("manifest_signature.txt", signature)
        zip_file.writestr("public_key.pem", signer.get_public_key_pem())
        
        # 1.2 Verification Instructions (US-66)
        verification_guide = """
# Verification Instructions

1. Extract `manifest.json`, `manifest_signature.txt`, and `public_key.pem`.
2. Use OpenSSL or a script to verify the signature against the public key.
3. Validate that `results.json` matches the published blockchain hash.
        """
        zip_file.writestr("VERIFICATION.md", verification_guide)
        
        # 2. Results (if available)
        if result:
            result_data = {
                "final_tally": result.final_tally,
                "verification_hash": result.verification_hash,
                "tx_hash": result.blockchain_tx_hash
            }
            zip_file.writestr("results.json", json.dumps(result_data, indent=2))
        
        # 3. Encryption Params
        if election.encryption_params:
            zip_file.writestr("encryption_params.json", json.dumps(election.encryption_params, indent=2))

    logging_service.log_event("evidence_download", "INFO", {"election_id": str(election_id)})

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=evidence_{election_id}.zip"
        }
    )

# US-70: Incident Response
@router.get("/incidents", response_model=List[IncidentResponse])
async def get_incidents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List system incidents."""
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()
    return incidents

@router.post("/incidents", response_model=IncidentResponse)
async def create_incident(
    incident: IncidentCreate,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor", "security_engineer"]))
):
    """Report a new incident."""
    db_incident = Incident(
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        reported_by=incident.reported_by,
        status="open"
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    
    logging_service.log_event("incident_created", "WARNING", {
        "incident_id": str(db_incident.incident_id),
        "severity": incident.severity
    })
    
    return db_incident

@router.put("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    incident_update: IncidentUpdate,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    """Update incident status or notes."""
    db_incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if incident_update.status:
        db_incident.status = incident_update.status
    if incident_update.resolution_notes:
        db_incident.resolution_notes = incident_update.resolution_notes
        
    db.commit()
    db.refresh(db_incident)
    
    logging_service.log_event("incident_updated", "INFO", {
        "incident_id": str(incident_id),
        "new_status": incident_update.status
    })
    
    return db_incident


# US-72: Compliance Reporting
@router.get("/compliance-report/{election_id}")
async def compliance_report(
    election_id: UUID,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    election = db.query(Election).filter(Election.election_id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    result = db.query(ElectionResult).filter(ElectionResult.election_id == election_id).first()
    audit_count = db.query(AuditLog).filter(AuditLog.election_id == election_id).count()
    chain_status = ledger_service.verify_chain(db, election_id)

    report = {
        "election_id": str(election_id),
        "controls": {
            "audit_logging": {"evidence": f"audit_logs:{audit_count}"},
            "ledger_integrity": {"evidence": chain_status},
            "result_verification": {"evidence": result.verification_hash if result else None}
        },
        "generated_at": datetime.utcnow().isoformat()
    }

    signature = signer.sign_data(report)
    report["signature"] = signature
    report["public_key"] = signer.get_public_key_pem()
    return report
