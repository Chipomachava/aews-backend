from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.health_report import HealthReport
from app.schemas.health_report import HealthReportResponse
from app.services.dependencies import require_role
from app.services.health_service import generate_health_snapshot

router = APIRouter(prefix="/health-reports", tags=["Health Reports"])


@router.post("/generate", response_model=HealthReportResponse)
def generate_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    snapshot = generate_health_snapshot(db)

    report = HealthReport(
        uptime=snapshot["uptime"],
        avgResponseTime=snapshot["avgResponseTime"],
        errorRate=snapshot["errorRate"],
        flaggedIssues=snapshot["flaggedIssues"],
        generatedBy=current_user.userID,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report