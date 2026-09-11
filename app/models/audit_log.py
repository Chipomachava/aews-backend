from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    logID = Column(Integer, primary_key=True, index=True)
    eventType = Column(String(50), nullable=False)  # e.g. LOGIN, UPLOAD, CONFIG_CHANGE
    description = Column(Text, nullable=False)
    userID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    targetEntity = Column(String(50), nullable=True)  # e.g. LecturerAccount
    targetID = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())