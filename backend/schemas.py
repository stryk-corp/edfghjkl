"""Pydantic request/response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from backend.models import UserRole, StageStatus, ClearanceStatus


# ── Auth ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    full_name: str


# ── User creation ────────────────────────────────────────────────────────

class StudentRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    matric_number: str
    department: str
    faculty: str
    level: int = 400
    graduation_year: int


class OfficerCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    department: str
    stage_order: int


# ── Profile responses ────────────────────────────────────────────────────

class StudentOut(BaseModel):
    id: str
    email: str
    full_name: str
    matric_number: str
    department: str
    faculty: str
    graduation_year: int

    class Config:
        from_attributes = True


class OfficerOut(BaseModel):
    id: str
    email: str
    full_name: str
    department: str
    stage_order: int

    class Config:
        from_attributes = True


# ── Clearance ────────────────────────────────────────────────────────────

class StageOut(BaseModel):
    id: str
    department: str
    order: int
    status: StageStatus
    remarks: Optional[str]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ClearanceRequestOut(BaseModel):
    id: str
    status: ClearanceStatus
    ai_risk_score: float
    ai_summary: Optional[str]
    submitted_at: datetime
    cleared_at: Optional[datetime]
    stages: List[StageOut] = []

    class Config:
        from_attributes = True


class StageDecision(BaseModel):
    stage_id: str
    decision: str          # "approved" | "rejected"
    remarks: Optional[str] = None


# ── Certificate ─────────────────────────────────────────────────────────

class CertificateOut(BaseModel):
    certificate_code: str
    issued_at: datetime
    student_name: str
    matric_number: str
    department: str
    faculty: str
    graduation_year: int
    is_revoked: bool

    class Config:
        from_attributes = True


# ── Analytics ───────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_students: int
    cleared: int
    in_progress: int
    rejected: int
    avg_processing_hours: float
    bottleneck_department: Optional[str]
