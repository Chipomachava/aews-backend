from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ThresholdConfiguration(Base):
    __tablename__ = "threshold_configurations"

    thresholdID = Column(Integer, primary_key=True, index=True)
    lowMax = Column(Float, nullable=False)
    mediumMax = Column(Float, nullable=False)  # must be > lowMax, enforced in service logic
    updatedBy = Column(Integer, ForeignKey("users.userID"))
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())