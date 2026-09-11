from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ConfigurationHistory(Base):
    __tablename__ = "configuration_history"

    historyID = Column(Integer, primary_key=True, index=True)
    configType = Column(String(30), nullable=False)  # Weight / Threshold / Indicator
    referenceID = Column(Integer, nullable=False)  # ID of the changed row
    oldValue = Column(String(100))
    newValue = Column(String(100))
    changedBy = Column(Integer, ForeignKey("users.userID"))
    changedAt = Column(DateTime(timezone=True), server_default=func.now())