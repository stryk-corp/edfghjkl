"""Authentication endpoints: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register/student", response_model=schemas.TokenResponse)
def register_student(data: schemas.StudentRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(models.StudentProfile).filter(
            models.StudentProfile.matric_number == data.matric_number).first():
        raise HTTPException(400, "Matric number already registered")

    user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=models.UserRole.student,
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(user)
    db.flush()

    profile = models.StudentProfile(
        user_id=user.id,
        matric_number=data.matric_number,
        department=data.department,
        faculty=data.faculty,
        level=data.level,
        graduation_year=data.graduation_year,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer",
            "role": user.role.value, "user_id": user.id, "full_name": user.full_name}


@router.post("/login", response_model=schemas.TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer",
            "role": user.role.value, "user_id": user.id, "full_name": user.full_name}


@router.get("/me")
def get_me(db: Session = Depends(get_db),
           current=Depends(__import__("backend.auth", fromlist=["get_current_user"]).get_current_user)):
    return {"id": current.id, "email": current.email,
            "full_name": current.full_name, "role": current.role.value}
