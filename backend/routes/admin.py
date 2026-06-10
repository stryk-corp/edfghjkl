"""Admin API: manage users, view analytics, audit logs."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend import models, schemas
from backend.auth import require_role, hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/officer", response_model=schemas.OfficerOut)
def create_officer(
    data: schemas.OfficerCreate,
    db: Session = Depends(get_db),
    current=Depends(require_role("admin"))
):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=models.UserRole.officer,
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(user)
    db.flush()

    profile = models.OfficerProfile(
        user_id=user.id,
        department=data.department,
        stage_order=data.stage_order,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "department": profile.department, "stage_order": profile.stage_order
    }


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(db: Session = Depends(get_db), current=Depends(require_role("admin"))):
    total     = db.query(models.StudentProfile).count()
    cleared   = db.query(models.ClearanceRequest).filter(
        models.ClearanceRequest.status == models.ClearanceStatus.cleared).count()
    in_prog   = db.query(models.ClearanceRequest).filter(
        models.ClearanceRequest.status == models.ClearanceStatus.in_progress).count()
    rejected  = db.query(models.ClearanceRequest).filter(
        models.ClearanceRequest.status == models.ClearanceStatus.rejected).count()

    # Average processing time (hours) for cleared requests
    cleared_reqs = (db.query(models.ClearanceRequest)
                    .filter(models.ClearanceRequest.cleared_at.isnot(None)).all())
    if cleared_reqs:
        hours = [
            (r.cleared_at - r.submitted_at).total_seconds() / 3600
            for r in cleared_reqs
        ]
        avg = sum(hours) / len(hours)
    else:
        avg = 0.0

    # Bottleneck: department with most pending stages
    row = (db.query(models.ClearanceStage.department,
                    func.count(models.ClearanceStage.id).label("cnt"))
           .filter(models.ClearanceStage.status == models.StageStatus.pending)
           .group_by(models.ClearanceStage.department)
           .order_by(func.count(models.ClearanceStage.id).desc())
           .first())
    bottleneck = row.department if row else None

    return {
        "total_students": total,
        "cleared": cleared,
        "in_progress": in_prog,
        "rejected": rejected,
        "avg_processing_hours": round(avg, 2),
        "bottleneck_department": bottleneck,
    }


@router.get("/students")
def list_students(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(require_role("admin"))
):
    qs = db.query(models.StudentProfile)
    if q:
        qs = qs.join(models.User).filter(
            models.User.full_name.ilike(f"%{q}%") |
            models.StudentProfile.matric_number.ilike(f"%{q}%")
        )
    profiles = qs.limit(100).all()
    return [{
        "id": p.id,
        "full_name": p.user.full_name,
        "email": p.user.email,
        "matric_number": p.matric_number,
        "department": p.department,
        "faculty": p.faculty,
        "graduation_year": p.graduation_year,
    } for p in profiles]


@router.get("/audit-logs")
def audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current=Depends(require_role("admin"))
):
    logs = (db.query(models.AuditLog)
            .order_by(models.AuditLog.timestamp.desc())
            .limit(limit).all())
    return [{
        "action": l.action, "entity_type": l.entity_type,
        "entity_id": l.entity_id, "details": l.details,
        "timestamp": l.timestamp.isoformat()
    } for l in logs]
