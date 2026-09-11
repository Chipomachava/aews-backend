from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    riskScoreID = Column(Integer, primary_key=True, index=True)
    studentID = Column(Integer, ForeignKey("students.studentID"), nullable=False)
    moduleID = Column(Integer, ForeignKey("modules.moduleID"), nullable=False)
    uploadID = Column(Integer, ForeignKey("csv_uploads.uploadID"), nullable=False)
    totalScore = Column(Float, nullable=False)
    riskLabel = Column(String(10), nullable=False)  # Low / Medium / High
    isPartial = Column(Boolean, nullable=False, default=False)
    computedAt = Column(DateTime(timezone=True), server_default=func.now())