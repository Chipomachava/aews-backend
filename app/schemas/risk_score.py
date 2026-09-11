from pydantic import BaseModel
from datetime import datetime


class RiskScoreResponse(BaseModel):
    riskScoreID: int
    studentID: int
    moduleID: int
    uploadID: int
    totalScore: float
    riskLabel: str
    isPartial: bool
    computedAt: datetime

    class Config:
        from_attributes = True