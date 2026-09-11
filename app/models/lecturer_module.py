from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class LecturerModule(Base):
    __tablename__ = "lecturer_modules"

    lecturerID = Column(Integer, ForeignKey("users.userID"), primary_key=True)
    moduleID = Column(Integer, ForeignKey("modules.moduleID"), primary_key=True)
    assignedAt = Column(DateTime(timezone=True), server_default=func.now())