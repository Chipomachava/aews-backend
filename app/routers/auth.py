from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.services.auth_service import verify_password, create_access_token, hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if not user or not verify_password(password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if user.status != "Active" and user.status != "Pending First Login":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    access_token = create_access_token(data={"userID": user.userID, "role": user.role.value})

    from app.services.audit_service import log_event
    log_event(db, eventType="LOGIN", description=f"{user.email} logged in", userID=user.userID)

    return Token(access_token=access_token)
from app.schemas.password import PasswordChange
from app.services.dependencies import get_current_user


@router.post("/change-password")
def change_password(
    password_in: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(password_in.currentPassword, current_user.passwordHash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    if len(password_in.newPassword) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")

    current_user.passwordHash = hash_password(password_in.newPassword)

    if current_user.status == "Pending First Login":
        current_user.status = "Active"

    db.commit()

    from app.services.audit_service import log_event
    log_event(db, eventType="PASSWORD_CHANGE", description=f"{current_user.email} changed their password", userID=current_user.userID)

    return {"message": "Password updated successfully"}