from datetime import date
from typing import Optional
from enum import Enum
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.intervention_note import InterventionNote
from app.services.dependencies import get_current_user, verify_module_access

router = APIRouter(prefix="/reports", tags=["Reports"])


class RiskLabelFilter(str, Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"


class InterventionStatusFilter(str, Enum):
    Open = "Open"
    Resolved = "Resolved"


@router.get("/students")
def generate_student_report(
    moduleID: int,
    riskLabel: Optional[RiskLabelFilter] = None,
    interventionStatus: Optional[InterventionStatusFilter] = None,
    dateFrom: Optional[date] = None,
    dateTo: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_module_access(moduleID, current_user, db)

    query = select(RiskScore).where(RiskScore.moduleID == moduleID)

    if riskLabel:
        query = query.where(RiskScore.riskLabel == riskLabel.value)
    if dateFrom:
        query = query.where(RiskScore.computedAt >= dateFrom)
    if dateTo:
        query = query.where(RiskScore.computedAt <= dateTo)

    risk_scores = db.execute(query.order_by(RiskScore.totalScore.desc())).scalars().all()

    report_rows = []
    for rs in risk_scores:
        student = db.get(Student, rs.studentID)

        interventions = db.execute(
            select(InterventionNote).where(InterventionNote.studentID == rs.studentID)
        ).scalars().all()

        if interventionStatus:
            interventions = [i for i in interventions if i.status == interventionStatus.value]
            if not interventions:
                continue

        report_rows.append({
            "studentID": rs.studentID,
            "studentNumber": student.studentNumber if student else None,
            "fullName": student.fullName if student else None,
            "totalScore": rs.totalScore,
            "riskLabel": rs.riskLabel,
            "isPartial": rs.isPartial,
            "computedAt": rs.computedAt,
            "openInterventions": len([i for i in interventions if i.status == "Open"]),
            "resolvedInterventions": len([i for i in interventions if i.status == "Resolved"]),
        })

    return {
        "moduleID": moduleID,
        "filters": {
            "riskLabel": riskLabel.value if riskLabel else None,
            "interventionStatus": interventionStatus.value if interventionStatus else None,
            "dateFrom": str(dateFrom) if dateFrom else None,
            "dateTo": str(dateTo) if dateTo else None,
        },
        "totalResults": len(report_rows),
        "results": report_rows,
    }