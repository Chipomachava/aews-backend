from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_event(
    db: Session,
    eventType: str,
    description: str,
    userID: int,
    targetEntity: str = None,
    targetID: int = None,
):
    entry = AuditLog(
        eventType=eventType,
        description=description,
        userID=userID,
        targetEntity=targetEntity,
        targetID=targetID,
    )
    db.add(entry)
    db.commit()