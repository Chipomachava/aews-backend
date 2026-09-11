from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import hash_password
from app.services.dependencies import require_role

router = APIRouter(prefix="/users", tags=["Users"])
@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    return db.execute(select(User)).scalars().all()


@router.post("/lecturer", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_lecturer(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    existing = db.execute(select(User).where(User.email == user_in.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    new_lecturer = User(
        fullName=user_in.fullName,
        email=user_in.email,
        passwordHash=hash_password(user_in.password),
        role=UserRole.Lecturer,
        staffNumber=user_in.staffNumber,
        status="Pending First Login",
    )
    db.add(new_lecturer)
    db.commit()
    db.refresh(new_lecturer)

    return new_lecturer
@router.patch("/{userID}/suspend")
def suspend_user(
    userID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    user = db.get(User, userID)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.Admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend an Admin account")

    user.status = "Suspended"
    db.commit()

    from app.services.audit_service import log_event
    log_event(db, eventType="USER_SUSPENDED", description=f"{user.email} suspended", userID=current_user.userID, targetEntity="User", targetID=user.userID)

    return {"message": f"{user.fullName} has been suspended"}


@router.patch("/{userID}/reactivate")
def reactivate_user(
    userID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    user = db.get(User, userID)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = "Active"
    db.commit()

    from app.services.audit_service import log_event
    log_event(db, eventType="USER_REACTIVATED", description=f"{user.email} reactivated", userID=current_user.userID, targetEntity="User", targetID=user.userID)

    return {"message": f"{user.fullName} has been reactivated"}
    from app.schemas.password import PasswordChange
from pydantic import BaseModel


class PasswordReset(BaseModel):
    newPassword: str


@router.patch("/{userID}/reset-password")
def reset_user_password(
    userID: int,
    reset_in: PasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    user = db.get(User, userID)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.Admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reset an Admin's password this way")

    if len(reset_in.newPassword) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")

    user.passwordHash = hash_password(reset_in.newPassword)
    user.status = "Pending First Login"
    db.commit()

    from app.services.audit_service import log_event
    log_event(db, eventType="PASSWORD_RESET", description=f"Admin reset password for {user.email}", userID=current_user.userID, targetEntity="User", targetID=user.userID)

    return {"message": f"Password reset for {user.fullName}. They must set a new password on next login."}