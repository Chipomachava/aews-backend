from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class InterventionNote(Base):
    __tablename__ = "intervention_notes"

    interventionID = Column(Integer, primary_key=True, index=True)
    studentID = Column(Integer, ForeignKey("students.studentID"), nullable=False)
    lecturerID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    interventionType = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    followUpDate = Column(Date, nullable=True)
    contextNote = Column(Text, nullable=True)
    riskLabelAtTime = Column(String(10), nullable=False)  # snapshot at time of intervention
    status = Column(String(20), nullable=False, default="Open")  # Open / Resolved
    outcomeNote = Column(Text, nullable=True)
    resolvedBy = Column(Integer, ForeignKey("users.userID"), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    resolvedAt = Column(DateTime(timezone=True), nullable=True)