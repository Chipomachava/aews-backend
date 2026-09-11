from sqlalchemy import Column, Integer, String
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    studentID = Column(Integer, primary_key=True, index=True)
    studentNumber = Column(String(20), unique=True, nullable=False, index=True)
    fullName = Column(String(120), nullable=False)