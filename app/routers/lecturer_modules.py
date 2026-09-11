from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.module import Module
from app.models.lecturer_module import LecturerModule
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/lecturer-modules", tags=["Lecturer-Module Assignment"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def assign_lecturer_to_module(
    lecturerID: int,
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    lecturer = db.get(User, lecturerID)
    if not lecturer or lecturer.role != UserRole.Lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecturer not found")

    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    existing = db.execute(
        select(LecturerModule).where(
            LecturerModule.lecturerID == lecturerID, LecturerModule.moduleID == moduleID
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lecturer already assigned to this module")

    assignment = LecturerModule(lecturerID=lecturerID, moduleID=moduleID)
    db.add(assignment)
    db.commit()

    return {"message": f"{lecturer.fullName} assigned to {module.moduleCode}"}


@router.get("/my-modules", response_model=list[dict])
def get_my_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignments = db.execute(
        select(LecturerModule).where(LecturerModule.lecturerID == current_user.userID)
    ).scalars().all()

    result = []
    for a in assignments:
        module = db.get(Module, a.moduleID)
        result.append({"moduleID": module.moduleID, "moduleCode": module.moduleCode, "moduleName": module.moduleName})

    return result