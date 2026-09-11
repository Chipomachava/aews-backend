from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class CSVUpload(Base):
    __tablename__ = "csv_uploads"

    uploadID = Column(Integer, primary_key=True, index=True)
    moduleID = Column(Integer, ForeignKey("modules.moduleID"), nullable=False)
    lecturerID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    fileName = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False)  # Success / Failed
    recordCount = Column(Integer, nullable=False, default=0)
    uploadedAt = Column(DateTime(timezone=True), server_default=func.now())