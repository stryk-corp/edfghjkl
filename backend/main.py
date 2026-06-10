"""
FastAPI application entry point.
Mounts all routers, serves static frontend files, and seeds demo data.
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.database import engine, Base, SessionLocal
from backend import models
from backend.auth import hash_password
from backend.routes.auth         import router as auth_router
from backend.routes.student      import router as student_router
from backend.routes.officer      import router as officer_router
from backend.routes.admin        import router as admin_router
from backend.routes.verification import router as verify_router

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="University Clearance System",
    description="AI-powered digital clearance & verification platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(student_router)
app.include_router(officer_router)
app.include_router(admin_router)
app.include_router(verify_router)

# ── QR verification shortcut (matches QR codes in certificates) ────────
@app.get("/verify/{code}", include_in_schema=False)
def verify_redirect(code: str):
    return RedirectResponse(url=f"/frontend/verify.html?code={code}")

# ── Static frontend ───────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/frontend/index.html")

# ── Seed demo data ─────────────────────────────────────────────────────
@app.on_event("startup")
def seed_demo_data():
    db = SessionLocal()
    try:
        # Admin user
        if not db.query(models.User).filter(models.User.email == "admin@university.edu").first():
            admin = models.User(
                email="admin@university.edu",
                hashed_password=hash_password("admin123"),
                role=models.UserRole.admin,
                full_name="System Administrator",
            )
            db.add(admin)
            db.flush()
            db.commit()
            print("✓ Demo admin: admin@university.edu / admin123")

        # Demo officer accounts
        demo_officers = [
            ("library@university.edu",  "officer123", "Library Officer",     "Library",             2),
            ("bursary@university.edu",   "officer123", "Bursary Officer",    "Bursary",             3),
            ("affairs@university.edu",   "officer123", "Student Affairs",    "Student Affairs",     4),
            ("dept@university.edu",      "officer123", "Dept. Officer",      "Academic Department", 1),
            ("hostel@university.edu",    "officer123", "Hostel Warden",      "Hostel",              5),
        ]
        for email, pwd, name, dept, order in demo_officers:
            if not db.query(models.User).filter(models.User.email == email).first():
                u = models.User(
                    email=email,
                    hashed_password=hash_password(pwd),
                    role=models.UserRole.officer,
                    full_name=name,
                )
                db.add(u)
                db.flush()
                p = models.OfficerProfile(user_id=u.id, department=dept, stage_order=order)
                db.add(p)
        db.commit()
        print("✓ Demo officers seeded  (password: officer123)")

        # Demo student
        if not db.query(models.User).filter(models.User.email == "student@university.edu").first():
            su = models.User(
                email="student@university.edu",
                hashed_password=hash_password("student123"),
                role=models.UserRole.student,
                full_name="Chukwuemeka Obi",
            )
            db.add(su)
            db.flush()
            sp = models.StudentProfile(
                user_id=su.id,
                matric_number="CSC/2020/001",
                department="Computer Science",
                faculty="Science",
                level=400,
                graduation_year=2025,
            )
            db.add(sp)
            db.commit()
            print("✓ Demo student: student@university.edu / student123")

    finally:
        db.close()
