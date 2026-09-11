from fastapi import FastAPI
from app.routers import auth
from app.routers import users
from app.routers import modules, students
from app.routers import enrollments
from app.routers import indicators
from app.routers import uploads
from app.routers import scoring_config
from app.routers import risk_scores
from app.routers import interventions
from app.routers import lecturer_modules
from app.routers import audit_logs
from app.routers import config_history
from app.routers import health_reports
from app.routers import reports

app = FastAPI(title="AEWS - Academic Early Warning System")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://aews-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(modules.router)
app.include_router(students.router)
app.include_router(enrollments.router)
app.include_router(indicators.router)
app.include_router(uploads.router)
app.include_router(scoring_config.router)
app.include_router(risk_scores.router)
app.include_router(interventions.router)
app.include_router(lecturer_modules.router)
app.include_router(audit_logs.router)
app.include_router(config_history.router)
app.include_router(health_reports.router)
app.include_router(reports.router)

@app.get("/")
def root():
    return {"message": "AEWS API is running"}
from fastapi import Depends
from app.services.dependencies import get_current_user, require_role
from app.models.user import User


@app.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"userID": current_user.userID, "email": current_user.email, "role": current_user.role.value}


@app.get("/admin-only")
def admin_only_route(current_user: User = Depends(require_role("Admin"))):
    return {"message": f"Welcome, Admin {current_user.fullName}"}