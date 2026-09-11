from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    fullName: str
    email: EmailStr
    role: UserRole
    staffNumber: Optional[str] = None


class UserCreate(UserBase):
    password: str  # plain password, hashed before storage


class UserResponse(UserBase):
    userID: int
    status: str
    createdAt: datetime

    class Config:
        from_attributes = True