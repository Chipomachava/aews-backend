from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class HealthReport(Base):
    __tablename__ = "health_reports"

    reportID = Column(Integer, primary_key=True, index=True)
    uptime = Column(Float, nullable=False)  # %
    avgResponseTime = Column(Float, nullable=False)  # ms
    errorRate = Column(Float, nullable=False)  # %
    flaggedIssues = Column(Text, nullable=True)  # components whose metric breached threshold
    generatedBy = Column(Integer, ForeignKey("users.userID"), nullable=False)
    generatedAt = Column(DateTime(timezone=True), server_default=func.now())