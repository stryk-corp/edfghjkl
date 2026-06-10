"""Public certificate verification endpoint."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models

router = APIRouter(prefix="/api/verify", tags=["Verification"])


@router.get("/{certificate_code}")
def verify_certificate(
    certificate_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    cert = (db.query(models.ClearanceCertificate)
            .filter(models.ClearanceCertificate.certificate_code == certificate_code)
            .first())
    if not cert:
        raise HTTPException(404, "Certificate not found")

    # Log the verification
    log = models.VerificationLog(
        certificate_id=cert.id,
        verifier_ip=request.client.host if request.client else "unknown",
    )
    db.add(log)
    db.commit()

    req     = cert.clearance_request
    profile = req.student
    user    = profile.user

    return {
        "valid": not cert.is_revoked,
        "certificate_code": cert.certificate_code,
        "issued_at": cert.issued_at.isoformat(),
        "student_name": user.full_name,
        "matric_number": profile.matric_number,
        "department": profile.department,
        "faculty": profile.faculty,
        "graduation_year": profile.graduation_year,
        "verification_count": len(cert.verifications),
    }
