from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuditLogResponse(BaseModel):
    logID: int
    eventType: str
    description: str
    userID: int
    targetEntity: Optional[str] = None
    targetID: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True