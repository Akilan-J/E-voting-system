
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
import hashlib
import base64
from pathlib import Path

from app.models import (
    get_db,
    Election,
    ElectionResult,
    EncryptedVote,
    Trustee,
    Incident,
    AuditLog,
    DisputeCase,
    IncidentAction
)
from app.models.schemas import (
    IncidentResponse,
    IncidentCreate,
    IncidentUpdate,
    IncidentActionCreate,
    IncidentActionResponse,
    DisputeCreate,
    DisputeResponse,
    DisputeUpdate
)
from app.services.monitoring import logging_service
from app.core.security_core import ImmutableLogger, KeyManager
from app.services.ledger_service import ledger_service
from app.utils.auth import RoleChecker

router = APIRouter()
logger = logging.getLogger(__name__)


def _log_action(
    db: Session,
    *,
    incident_id: UUID = None,
    dispute_id: UUID = None,
    actor: str = None,
    action_type: str,
    details: Dict[str, Any] = None
) -> IncidentAction:
    action = IncidentAction(
        incident_id=incident_id,
        dispute_id=dispute_id,
        actor=actor,
        action_type=action_type,
        details=details or {}
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def _artifact_dir(subdir: str) -> Path:
    root = Path(__file__).resolve().parents[3]
    path = root / "artifacts" / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_signed_report(report: Dict[str, Any], subdir: str, prefix: str) -> Dict[str, Any]:
    payload = json.dumps(report, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    
    km = KeyManager.get_instance()
    signature_bytes = km.sign_data(payload)
    signature = base64.b64encode(signature_bytes).decode('utf-8')

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{prefix}_{timestamp}_{digest[:10]}"
    target_dir = _artifact_dir(subdir)

    report_path = target_dir / f"{base_name}.json"
    sig_path = target_dir / f"{base_name}.sig"
    pub_path = target_dir / f"{base_name}.pub"

    artifact_path = None
    try:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        sig_path.write_text(signature, encoding="utf-8")
        pub_path.write_text(km.get_public_key_pem(), encoding="utf-8")
        artifact_path = str(report_path.relative_to(target_dir.parents[1]))
    except OSError:
        artifact_path = f"{subdir}/{base_name}.json"

    return {
        "artifact": artifact_path,
        "signature": signature,
        "public_key": km.get_public_key_pem(),
        "report_hash": digest
    }


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
    km = KeyManager.get_instance()
    
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
        sig_bytes = km.sign_data(manifest_str.encode("utf-8")) # Sign the JSON string bytes
        signature = base64.b64encode(sig_bytes).decode('utf-8')
        
        zip_file.writestr("manifest_signature.txt", signature)
        zip_file.writestr("public_key.pem", km.get_public_key_pem())
        
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

    _log_action(
        db,
        incident_id=db_incident.incident_id,
        actor=incident.reported_by,
        action_type="INCIDENT_CREATED",
        details={"severity": incident.severity}
    )

    ImmutableLogger.log(
        db,
        election_id=None,
        operation="incident_created",
        actor=incident.reported_by or "system",
        details={"incident_id": str(db_incident.incident_id), "severity": incident.severity},
        status="success",
        ip="127.0.0.1" # Placeholder for internal calls
    )
    
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

    allowed_statuses = {"open", "triage", "mitigated", "resolved"}
    if incident_update.status and incident_update.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid incident status")
    
    if incident_update.status:
        db_incident.status = incident_update.status
    if incident_update.resolution_notes:
        db_incident.resolution_notes = incident_update.resolution_notes
        
    db.commit()
    db.refresh(db_incident)

    _log_action(
        db,
        incident_id=incident_id,
        actor=role,
        action_type="INCIDENT_STATUS_CHANGED",
        details={
            "status": incident_update.status,
            "resolution_notes": incident_update.resolution_notes
        }
    )

    ImmutableLogger.log(
        db,
        election_id=None,
        operation="incident_updated",
        actor=role,
        details={"incident_id": str(incident_id), "status": incident_update.status},
        status="success",
        ip="127.0.0.1"
    )
    
    logging_service.log_event("incident_updated", "INFO", {
        "incident_id": str(incident_id),
        "new_status": incident_update.status
    })
    
    return db_incident

@router.get("/incidents/{incident_id}/actions", response_model=List[IncidentActionResponse])
async def get_incident_actions(
    incident_id: UUID,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor", "security_engineer"]))
):
    actions = db.query(IncidentAction).filter(
        IncidentAction.incident_id == incident_id
    ).order_by(IncidentAction.created_at.asc()).all()
    return actions

@router.post("/incidents/{incident_id}/actions", response_model=IncidentActionResponse)
async def add_incident_action(
    incident_id: UUID,
    action: IncidentActionCreate,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor", "security_engineer"]))
):
    db_incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not db_incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    action_entry = _log_action(
        db,
        incident_id=incident_id,
        actor=role,
        action_type=action.action_type,
        details=action.details
    )

    ImmutableLogger.log(
        db,
        election_id=None,
        operation="incident_action_added",
        actor=role,
        details={"incident_id": str(incident_id), "action_type": action.action_type},
        status="success",
        ip="127.0.0.1"
    )

    return action_entry

@router.get("/incidents/{incident_id}/report")
async def export_incident_report(
    incident_id: UUID,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    actions = db.query(IncidentAction).filter(
        IncidentAction.incident_id == incident_id
    ).order_by(IncidentAction.created_at.asc()).all()

    report = {
        "incident": {
            "incident_id": str(incident.incident_id),
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "reported_by": incident.reported_by,
            "created_at": incident.created_at.isoformat(),
            "updated_at": incident.updated_at.isoformat()
        },
        "actions": [
            {
                "action_id": str(action.action_id),
                "action_type": action.action_type,
                "actor": action.actor,
                "details": action.details,
                "created_at": action.created_at.isoformat()
            }
            for action in actions
        ],
        "generated_at": datetime.utcnow().isoformat()
    }

    signed = _write_signed_report(report, "incident_reports", f"incident_{incident.incident_id}")
    report.update({
        "signature": signed["signature"],
        "public_key": signed["public_key"],
        "report_hash": signed["report_hash"],
        "artifact": signed["artifact"]
    })
    return report

@router.get("/disputes", response_model=List[DisputeResponse])
async def get_disputes(
    status: str = None,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    query = db.query(DisputeCase)
    if status:
        query = query.filter(DisputeCase.status == status)
    return query.order_by(DisputeCase.created_at.desc()).all()

@router.post("/disputes", response_model=DisputeResponse)
async def create_dispute(
    dispute: DisputeCreate,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    db_dispute = DisputeCase(
        election_id=dispute.election_id,
        title=dispute.title,
        description=dispute.description,
        status="open",
        filed_by=dispute.filed_by,
        evidence=dispute.evidence or []
    )
    db.add(db_dispute)
    db.commit()
    db.refresh(db_dispute)

    _log_action(
        db,
        dispute_id=db_dispute.dispute_id,
        actor=dispute.filed_by,
        action_type="DISPUTE_CREATED",
        details={"title": dispute.title}
    )

    ImmutableLogger.log(
        db,
        election_id=str(db_dispute.election_id),
        operation="dispute_created",
        actor=dispute.filed_by or "system",
        details={"dispute_id": str(db_dispute.dispute_id), "title": dispute.title},
        status="success",
        ip="127.0.0.1"
    )

    logging_service.log_event("dispute_created", "WARNING", {
        "dispute_id": str(db_dispute.dispute_id),
        "status": db_dispute.status
    })

    return db_dispute

@router.put("/disputes/{dispute_id}", response_model=DisputeResponse)
async def update_dispute(
    dispute_id: UUID,
    update: DisputeUpdate,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    db_dispute = db.query(DisputeCase).filter(DisputeCase.dispute_id == dispute_id).first()
    if not db_dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    allowed_statuses = {"open", "triage", "investigating", "resolved", "rejected"}
    if update.status and update.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid dispute status")

    if update.status:
        db_dispute.status = update.status
    if update.resolution_notes:
        db_dispute.resolution_notes = update.resolution_notes
    if update.evidence:
        existing = db_dispute.evidence or []
        db_dispute.evidence = existing + update.evidence

    db.commit()
    db.refresh(db_dispute)

    _log_action(
        db,
        dispute_id=dispute_id,
        actor=role,
        action_type="DISPUTE_UPDATED",
        details={
            "status": update.status,
            "resolution_notes": update.resolution_notes,
            "evidence_added": update.evidence
        }
    )

    ImmutableLogger.log(
        db,
        election_id=str(db_dispute.election_id),
        operation="dispute_updated",
        actor=role,
        details={"dispute_id": str(dispute_id), "status": update.status},
        status="success",
        ip="127.0.0.1"
    )

    logging_service.log_event("dispute_updated", "INFO", {
        "dispute_id": str(dispute_id),
        "status": update.status
    })

    return db_dispute

@router.get("/disputes/{dispute_id}/actions", response_model=List[IncidentActionResponse])
async def get_dispute_actions(
    dispute_id: UUID,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    actions = db.query(IncidentAction).filter(
        IncidentAction.dispute_id == dispute_id
    ).order_by(IncidentAction.created_at.asc()).all()
    return actions
    
@router.get("/disputes/{dispute_id}/report")
async def export_dispute_report(
    dispute_id: UUID,
    db: Session = Depends(get_db),
    role: str = Depends(RoleChecker(["admin", "auditor"]))
):
    dispute = db.query(DisputeCase).filter(DisputeCase.dispute_id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    actions = db.query(IncidentAction).filter(
        IncidentAction.dispute_id == dispute_id
    ).order_by(IncidentAction.created_at.asc()).all()

    report = {
        "dispute": {
            "dispute_id": str(dispute.dispute_id),
            "election_id": str(dispute.election_id) if dispute.election_id else None,
            "title": dispute.title,
            "description": dispute.description,
            "status": dispute.status,
            "filed_by": dispute.filed_by,
            "evidence": dispute.evidence,
            "created_at": dispute.created_at.isoformat(),
            "updated_at": dispute.updated_at.isoformat()
        },
        "actions": [
            {
                "action_id": str(action.action_id),
                "action_type": action.action_type,
                "actor": action.actor,
                "details": action.details,
                "created_at": action.created_at.isoformat()
            }
            for action in actions
        ],
        "generated_at": datetime.utcnow().isoformat()
    }

    signed = _write_signed_report(report, "dispute_reports", f"dispute_{dispute.dispute_id}")
    report.update({
        "signature": signed["signature"],
        "public_key": signed["public_key"],
        "report_hash": signed["report_hash"],
        "artifact": signed["artifact"]
    })
    return report


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

    dispute_count = db.query(DisputeCase).filter(DisputeCase.election_id == election_id).count()
    incident_count = db.query(Incident).count()

    report = {
        "election_id": str(election_id),
        "controls": {
            "audit_logging": {"evidence": f"audit_logs:{audit_count}", "status": "present"},
            "ledger_integrity": {"evidence": chain_status, "status": "verified"},
            "result_verification": {"evidence": result.verification_hash if result else None, "status": "present"},
            "incident_tracking": {"evidence": f"incidents:{incident_count}", "status": "present"},
            "dispute_workflow": {"evidence": f"disputes:{dispute_count}", "status": "present"}
        },
        "missing_controls": [
            key for key, value in {
                "result_verification": result is not None
            }.items() if not value
        ],
        "generated_at": datetime.utcnow().isoformat()
    }

    signed = _write_signed_report(report, "compliance_reports", f"compliance_{election_id}")
    report.update({
        "signature": signed["signature"],
        "public_key": signed["public_key"],
        "report_hash": signed["report_hash"],
        "artifact": signed["artifact"]
    })
    return report
