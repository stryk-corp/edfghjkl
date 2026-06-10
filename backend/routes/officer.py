"""Officer API: view pending students, approve/reject stages."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import require_role
from backend.ai_engine import summarise_queue
from backend.certificate_gen import generate_certificate
import uuid

router = APIRouter(prefix="/api/officer", tags=["Officer"])


def _check_and_finalize(clearance_req: models.ClearanceRequest, db: Session):
    """If all stages are approved, mark the clearance cleared and generate a certificate."""
    stages = clearance_req.stages
    if all(s.status == models.StageStatus.approved for s in stages):
        clearance_req.status = models.ClearanceStatus.cleared
        clearance_req.cleared_at = datetime.utcnow()
        db.flush()

        profile = clearance_req.student
        user    = profile.user
        code    = f"CL-{profile.graduation_year}-{str(uuid.uuid4())[:8].upper()}"
        pdf_path = generate_certificate(
            certificate_code=code,
            student_name=user.full_name,
            matric_number=profile.matric_number,
            department=profile.department,
            faculty=profile.faculty,
            graduation_year=profile.graduation_year,
        )
        cert = models.ClearanceCertificate(
            clearance_request_id=clearance_req.id,
            certificate_code=code,
            pdf_path=pdf_path,
        )
        db.add(cert)
        db.commit()

    elif any(s.status == models.StageStatus.rejected for s in stages):
        clearance_req.status = models.ClearanceStatus.rejected
        db.commit()


@router.get("/pending")
def get_pending(
    db: Session = Depends(get_db),
    current=Depends(require_role("officer"))
):
    officer_profile = current.officer_profile
    if not officer_profile:
        raise HTTPException(404, "Officer profile not found")

    stages = (
        db.query(models.ClearanceStage)
        .filter(models.ClearanceStage.department == officer_profile.department)
        .filter(models.ClearanceStage.status == models.StageStatus.pending)
        .all()
    )

    result = []
    for stage in stages:
        req  = stage.clearance_request
        prof = req.student
        user = prof.user
        docs = [
            {
                "type": d.document_type,
                "filename": d.original_filename,
                "ai_result": json.loads(d.ai_validation_result) if d.ai_validation_result else {},
            }
            for d in req.documents
        ]
        result.append({
            "stage_id": stage.id,
            "clearance_id": req.id,
            "student_name": user.full_name,
            "matric_number": prof.matric_number,
            "department": prof.department,
            "faculty": prof.faculty,
            "submitted_at": req.submitted_at.isoformat(),
            "risk_score": req.ai_risk_score,
            "documents": docs,
        })

    return {
        "pending": result,
        "ai_summary": summarise_queue(result),
    }


@router.post("/decide")
def decide_stage(
    body: schemas.StageDecision,
    db: Session = Depends(get_db),
    current=Depends(require_role("officer"))
):
    stage = db.query(models.ClearanceStage).filter(
        models.ClearanceStage.id == body.stage_id).first()
    if not stage:
        raise HTTPException(404, "Stage not found")

    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "Decision must be 'approved' or 'rejected'")

    stage.status      = models.StageStatus.approved if body.decision == "approved"                                 else models.StageStatus.rejected
    stage.remarks     = body.remarks
    stage.reviewed_at = datetime.utcnow()
    stage.officer_id  = current.officer_profile.id if current.officer_profile else None
    db.flush()

    _check_and_finalize(stage.clearance_request, db)
    return {"message": f"Stage {body.decision} successfully"}


@router.post("/chat")
def officer_chat(body: dict, current=Depends(require_role("officer"))):
    from backend.ai_engine import chat
    return {"reply": chat(body.get("messages", []))}
