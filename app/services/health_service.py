from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.csv_upload import CSVUpload
from app.models.audit_log import AuditLog


def generate_health_snapshot(db: Session):
    """
    Computes a real snapshot from recorded system activity:
    - errorRate: % of CSV uploads that failed validation (last 50 uploads)
    - uptime: placeholder at 100% (no infra monitoring integrated yet)
    - avgResponseTime: placeholder (would need request-timing middleware)
    """
    recent_uploads = db.execute(
        select(CSVUpload).order_by(CSVUpload.uploadedAt.desc()).limit(50)
    ).scalars().all()

    total = len(recent_uploads)
    failed = len([u for u in recent_uploads if u.status == "Failed"])
    error_rate = round((failed / total) * 100, 2) if total > 0 else 0.0

    flagged = []
    if error_rate > 20:
        flagged.append("High CSV upload failure rate")

    return {
        "uptime": 100.0,
        "avgResponseTime": 0.0,
        "errorRate": error_rate,
        "flaggedIssues": ", ".join(flagged) if flagged else None,
    }