from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.configuration_history import ConfigurationHistory
from app.services.dependencies import require_role

router = APIRouter(prefix="/config-history", tags=["Configuration History"])


@router.get("/")
def list_config_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    entries = db.execute(select(ConfigurationHistory).order_by(ConfigurationHistory.changedAt.desc())).scalars().all()
    return [
        {
            "historyID": e.historyID,
            "configType": e.configType,
            "referenceID": e.referenceID,
            "oldValue": e.oldValue,
            "newValue": e.newValue,
            "changedBy": e.changedBy,
            "changedAt": e.changedAt,
        }
        for e in entries
    ]