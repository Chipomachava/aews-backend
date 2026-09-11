from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HealthReportResponse(BaseModel):
    reportID: int
    uptime: float
    avgResponseTime: float
    errorRate: float
    flaggedIssues: Optional[str] = None
    generatedBy: int
    generatedAt: datetime

    class Config:
        from_attributes = True