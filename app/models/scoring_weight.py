from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ScoringWeight(Base):
    __tablename__ = "scoring_weights"

    weightID = Column(Integer, primary_key=True, index=True)
    indicatorID = Column(Integer, ForeignKey("academic_indicators.indicatorID"), unique=True, nullable=False)
    weightValue = Column(Float, nullable=False)  # must be >= 0, enforced in service logic
    updatedBy = Column(Integer, ForeignKey("users.userID"))
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())