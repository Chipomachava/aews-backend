from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.risk_score import RiskScore
from app.models.intervention_note import InterventionNote
from app.schemas.intervention_note import (
    InterventionNoteCreate,
    InterventionNoteResolve,
    InterventionNoteResponse,
)
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/interventions", tags=["Interventions"])


@router.post("/", response_model=InterventionNoteResponse, status_code=status.HTTP_201_CREATED)
def record_intervention(
    intervention_in: InterventionNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    latest_score = db.execute(
        select(RiskScore)
        .where(RiskScore.studentID == intervention_in.studentID)
        .order_by(RiskScore.computedAt.desc())
    ).scalars().first()

    risk_label_at_time = latest_score.riskLabel if latest_score else "Unknown"

    new_intervention = InterventionNote(
        studentID=intervention_in.studentID,
        lecturerID=current_user.userID,
        interventionType=intervention_in.interventionType,
        description=intervention_in.description,
        followUpDate=intervention_in.followUpDate,
        contextNote=intervention_in.contextNote,
        riskLabelAtTime=risk_label_at_time,
        status="Open",
    )
    db.add(new_intervention)
    db.commit()
    db.refresh(new_intervention)
    return new_intervention


@router.get("/", response_model=list[InterventionNoteResponse])
def list_interventions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "Admin":
        return db.execute(select(InterventionNote)).scalars().all()

    from app.models.lecturer_module import LecturerModule
    from app.models.enrollment import Enrollment

    my_module_ids = db.execute(
        select(LecturerModule.moduleID).where(LecturerModule.lecturerID == current_user.userID)
    ).scalars().all()

    if not my_module_ids:
        return []

    my_student_ids = db.execute(
        select(Enrollment.studentID).where(Enrollment.moduleID.in_(my_module_ids))
    ).scalars().all()

    return db.execute(
        select(InterventionNote).where(InterventionNote.studentID.in_(my_student_ids))
    ).scalars().all()


@router.patch("/{interventionID}/resolve", response_model=InterventionNoteResponse)
def resolve_intervention(
    interventionID: int,
    resolve_in: InterventionNoteResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    from datetime import datetime, timezone

    intervention = db.get(InterventionNote, interventionID)
    if not intervention:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")

    if intervention.status == "Resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Intervention already resolved")

    intervention.status = "Resolved"
    intervention.outcomeNote = resolve_in.outcomeNote
    intervention.resolvedBy = current_user.userID
    intervention.resolvedAt = datetime.now(timezone.utc)

    db.commit()
    db.refresh(intervention)
    return intervention
    from pydantic import BaseModel


class NotifyRequest(BaseModel):
    channel: str  # "Email" or "SMS"
    message: str


@router.post("/{interventionID}/notify")
def notify_student(
    interventionID: int,
    notify_in: NotifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = db.get(InterventionNote, interventionID)
    if not intervention:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")

    from app.models.student import Student
    student = db.get(Student, intervention.studentID)

    from app.services.audit_service import log_event
    log_event(
        db,
        eventType="NOTIFICATION_SIMULATED",
        description=f"{notify_in.channel} notification (simulated) to {student.fullName if student else 'student'}: \"{notify_in.message}\"",
        userID=current_user.userID,
        targetEntity="InterventionNote",
        targetID=interventionID,
    )

    return {"message": f"{notify_in.channel} notification logged (simulated - no real delivery configured yet)"}