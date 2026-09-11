from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.academic_indicator import AcademicIndicator
from app.schemas.academic_indicator import AcademicIndicatorCreate, AcademicIndicatorResponse
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/indicators", tags=["Indicators"])


@router.post("/", response_model=AcademicIndicatorResponse, status_code=status.HTTP_201_CREATED)
def create_indicator(
    indicator_in: AcademicIndicatorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    existing = db.execute(
        select(AcademicIndicator).where(AcademicIndicator.name == indicator_in.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indicator name already exists")

    new_indicator = AcademicIndicator(**indicator_in.model_dump())
    db.add(new_indicator)
    db.commit()
    db.refresh(new_indicator)
    return new_indicator


@router.get("/", response_model=list[AcademicIndicatorResponse])
def list_indicators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(select(AcademicIndicator)).scalars().all()