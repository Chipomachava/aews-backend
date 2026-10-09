from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class InterventionNoteCreate(BaseModel):
    studentID: int
    interventionType: str
    description: str
    followUpDate: Optional[date] = None
    contextNote: Optional[str] = None


class InterventionNoteResolve(BaseModel):
    outcomeNote: str


class InterventionNoteResponse(BaseModel):
    interventionID: int
    studentID: int
    studentNumber: Optional[str] = None
    studentInitials: Optional[str] = None
    lecturerID: int
    interventionType: str
    description: str
    followUpDate: Optional[date] = None
    contextNote: Optional[str] = None
    riskLabelAtTime: str
    status: str
    outcomeNote: Optional[str] = None
    resolvedBy: Optional[int] = None
    createdAt: datetime
    resolvedAt: Optional[datetime] = None

    class Config:
        from_attributes = True