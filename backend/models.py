"""SQLAlchemy ORM models for every entity in the clearance system."""
import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Integer, DateTime, Boolean,
                        ForeignKey, Text, Float, Enum as SAEnum)
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


def gen_id():
    return str(uuid.uuid4())


# ── Enumerations ────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    student  = "student"
    officer  = "officer"
    admin    = "admin"


class StageStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped  = "skipped"


class ClearanceStatus(str, enum.Enum):
    in_progress = "in_progress"
    cleared     = "cleared"
    rejected    = "rejected"


# ── Users ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=gen_id)
    email         = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role          = Column(SAEnum(UserRole), nullable=False)
    full_name     = Column(String, nullable=False)
    phone         = Column(String)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Role-specific child rows
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    officer_profile = relationship("OfficerProfile", back_populates="user", uselist=False)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id             = Column(String, primary_key=True, default=gen_id)
    user_id        = Column(String, ForeignKey("users.id"), unique=True)
    matric_number  = Column(String, unique=True, index=True, nullable=False)
    department     = Column(String, nullable=False)
    faculty        = Column(String, nullable=False)
    level          = Column(Integer, nullable=False, default=400)
    graduation_year = Column(Integer, nullable=False)

    user            = relationship("User", back_populates="student_profile")
    clearance_requests = relationship("ClearanceRequest", back_populates="student")


class OfficerProfile(Base):
    __tablename__ = "officer_profiles"

    id          = Column(String, primary_key=True, default=gen_id)
    user_id     = Column(String, ForeignKey("users.id"), unique=True)
    department  = Column(String, nullable=False)   # e.g. "Library"
    stage_order = Column(Integer, nullable=False)  # processing order

    user   = relationship("User", back_populates="officer_profile")
    stages = relationship("ClearanceStage", back_populates="officer")


# ── Clearance Workflow ────────────────────────────────────────────────────

class ClearanceRequest(Base):
    __tablename__ = "clearance_requests"

    id          = Column(String, primary_key=True, default=gen_id)
    student_id  = Column(String, ForeignKey("student_profiles.id"))
    status      = Column(SAEnum(ClearanceStatus), default=ClearanceStatus.in_progress)
    ai_risk_score = Column(Float, default=0.0)
    ai_summary  = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    cleared_at  = Column(DateTime)
    cert_path   = Column(String)          # path to generated PDF

    student     = relationship("StudentProfile", back_populates="clearance_requests")
    documents   = relationship("Document", back_populates="clearance_request")
    stages      = relationship("ClearanceStage", back_populates="clearance_request",
                               order_by="ClearanceStage.order")
    certificate = relationship("ClearanceCertificate", back_populates="clearance_request",
                               uselist=False)


class ClearanceStage(Base):
    __tablename__ = "clearance_stages"

    id                  = Column(String, primary_key=True, default=gen_id)
    clearance_request_id = Column(String, ForeignKey("clearance_requests.id"))
    department          = Column(String, nullable=False)
    order               = Column(Integer, nullable=False)
    status              = Column(SAEnum(StageStatus), default=StageStatus.pending)
    officer_id          = Column(String, ForeignKey("officer_profiles.id"), nullable=True)
    remarks             = Column(Text)
    reviewed_at         = Column(DateTime)

    clearance_request   = relationship("ClearanceRequest", back_populates="stages")
    officer             = relationship("OfficerProfile", back_populates="stages")


class Document(Base):
    __tablename__ = "documents"

    id                  = Column(String, primary_key=True, default=gen_id)
    clearance_request_id = Column(String, ForeignKey("clearance_requests.id"))
    document_type       = Column(String, nullable=False)  # e.g. "school_fee_receipt"
    file_path           = Column(String, nullable=False)
    original_filename   = Column(String)
    ai_extracted_text   = Column(Text)
    ai_validation_result = Column(Text)   # JSON string
    uploaded_at         = Column(DateTime, default=datetime.utcnow)

    clearance_request   = relationship("ClearanceRequest", back_populates="documents")


class ClearanceCertificate(Base):
    __tablename__ = "clearance_certificates"

    id                  = Column(String, primary_key=True, default=gen_id)
    clearance_request_id = Column(String, ForeignKey("clearance_requests.id"), unique=True)
    certificate_code    = Column(String, unique=True, index=True)
    issued_at           = Column(DateTime, default=datetime.utcnow)
    pdf_path            = Column(String)
    qr_code_path        = Column(String)
    is_revoked          = Column(Boolean, default=False)

    clearance_request   = relationship("ClearanceRequest", back_populates="certificate")
    verifications       = relationship("VerificationLog", back_populates="certificate")


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id              = Column(String, primary_key=True, default=gen_id)
    certificate_id  = Column(String, ForeignKey("clearance_certificates.id"))
    verified_at     = Column(DateTime, default=datetime.utcnow)
    verifier_ip     = Column(String)
    verifier_note   = Column(String)

    certificate     = relationship("ClearanceCertificate", back_populates="verifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(String, primary_key=True, default=gen_id)
    user_id     = Column(String, ForeignKey("users.id"), nullable=True)
    action      = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id   = Column(String)
    details     = Column(Text)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    ip_address  = Column(String)
