from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    studentID = Column(Integer, ForeignKey("students.studentID"), primary_key=True)
    moduleID = Column(Integer, ForeignKey("modules.moduleID"), primary_key=True)