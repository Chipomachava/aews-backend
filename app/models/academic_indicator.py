from sqlalchemy import Column, Integer, String, Float, Boolean
from app.database import Base


class AcademicIndicator(Base):
    __tablename__ = "academic_indicators"

    indicatorID = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), unique=True, nullable=False)
    dataType = Column(String(20), nullable=False)  # Numeric / Percentage
    minValue = Column(Float, nullable=False)
    maxValue = Column(Float, nullable=False)
    isActive = Column(Boolean, nullable=False, default=True)
    higherIsBetter = Column(Boolean, nullable=False, default=True)