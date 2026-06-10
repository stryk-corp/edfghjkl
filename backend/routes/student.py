"""Student-facing API: submit clearance, upload docs, check status, chat."""
import os, shutil, json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import require_role
from backend.ai_engine import validate_document, chat

router = APIRouter(prefix="/api/student", tags=["Student"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

REQUIRED_DOCS = [
    "school_fee_receipt",
    "departmental_clearance",
    "library_clearance",
    "student_id",
]

CLEARANCE_STAGES = [
    {"department": "Academic Department", "order": 1},
    {"department": "Library",             "order": 2},
    {"department": "Bursary",             "order": 3},
    {"department": "Student Affairs",     "order": 4},
    {"department": "Hostel",              "order": 5},
]


@router.post("/clearance/start")
def start_clearance(
    db: Session = Depends(get_db),
    current=Depends(require_role("student"))
):
    profile = current.student_profile
    if not profile:
        raise HTTPException(404, "Student profile not found")

    existing = (db.query(models.ClearanceRequest)
                .filter(models.ClearanceRequest.student_id == profile.id)
                .filter(models.ClearanceRequest.status == models.ClearanceStatus.in_progress)
                .first())
    if existing:
        return {"clearance_id": existing.id, "message": "Clearance already in progress"}

    req = models.ClearanceRequest(student_id=profile.id)
    db.add(req)
    db.flush()

    for s in CLEARANCE_STAGES:
        stage = models.ClearanceStage(
            clearance_request_id=req.id,
            department=s["department"],
            order=s["order"],
        )
        db.add(stage)

    db.commit()
    db.refresh(req)
    return {"clearance_id": req.id, "message": "Clearance process started"}


@router.post("/clearance/{clearance_id}/upload")
async def upload_document(
    clearance_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current=Depends(require_role("student"))
):
    req = db.query(models.ClearanceRequest).filter(
        models.ClearanceRequest.id == clearance_id).first()
    if not req:
        raise HTTPException(404, "Clearance request not found")
    if req.student.user_id != current.id:
        raise HTTPException(403, "Not your clearance")

    # Save file
    dest_dir = os.path.join(UPLOAD_DIR, clearance_id)
    os.makedirs(dest_dir, exist_ok=True)
    safe_name = f"{document_type}_{file.filename}"
    dest = os.path.join(dest_dir, safe_name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # AI validation
    profile = current.student_profile
    result = validate_document(
        dest, document_type, profile.matric_number, current.full_name
    )

    doc = models.Document(
        clearance_request_id=clearance_id,
        document_type=document_type,
        file_path=dest,
        original_filename=file.filename,
        ai_validation_result=json.dumps(result),
    )
    db.add(doc)
    db.commit()

    return {
        "message": "Document uploaded",
        "ai_result": result
    }


@router.get("/clearance/status", response_model=schemas.ClearanceRequestOut)
def get_clearance_status(
    db: Session = Depends(get_db),
    current=Depends(require_role("student"))
):
    profile = current.student_profile
    req = (db.query(models.ClearanceRequest)
           .filter(models.ClearanceRequest.student_id == profile.id)
           .order_by(models.ClearanceRequest.submitted_at.desc())
           .first())
    if not req:
        raise HTTPException(404, "No clearance request found")
    return req


@router.get("/certificate/download")
def download_certificate(
    db: Session = Depends(get_db),
    current=Depends(require_role("student"))
):
    profile = current.student_profile
    req = (db.query(models.ClearanceRequest)
           .filter(models.ClearanceRequest.student_id == profile.id)
           .filter(models.ClearanceRequest.status == models.ClearanceStatus.cleared)
           .first())
    if not req or not req.certificate:
        raise HTTPException(404, "No certificate found")
    return FileResponse(req.certificate.pdf_path, media_type="application/pdf",
                        filename=f"clearance_{profile.matric_number}.pdf")


@router.post("/chat")
def student_chat(
    body: dict,
    db: Session = Depends(get_db),
    current=Depends(require_role("student"))
):
    messages = body.get("messages", [])
    reply = chat(messages)
    return {"reply": reply}
