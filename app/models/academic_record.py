from sqlalchemy import Column, Integer, Float, ForeignKey
from app.database import Base


class AcademicRecord(Base):
    __tablename__ = "academic_records"

    recordID = Column(Integer, primary_key=True, index=True)
    uploadID = Column(Integer, ForeignKey("csv_uploads.uploadID"), nullable=False)
    studentID = Column(Integer, ForeignKey("students.studentID"), nullable=False)
    indicatorID = Column(Integer, ForeignKey("academic_indicators.indicatorID"), nullable=False)
    rawValue = Column(Float, nullable=False)