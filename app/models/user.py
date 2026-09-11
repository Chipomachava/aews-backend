from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    Admin = "Admin"
    Lecturer = "Lecturer"


class User(Base):
    __tablename__ = "users"

    userID = Column(Integer, primary_key=True, index=True)
    fullName = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    passwordHash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    staffNumber = Column(String(30), nullable=True)
    status = Column(String(30), nullable=False, default="Pending First Login")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())