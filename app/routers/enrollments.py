from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.module import Module
from app.models.enrollment import Enrollment
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def enroll_student(
    studentID: int,
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    student = db.get(Student, studentID)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    existing = db.execute(
        select(Enrollment).where(Enrollment.studentID == studentID, Enrollment.moduleID == moduleID)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already enrolled in this module")

    enrollment = Enrollment(studentID=studentID, moduleID=moduleID)
    db.add(enrollment)
    db.commit()

    return {"message": f"{student.fullName} enrolled in {module.moduleCode}"}
@router.get("/module/{moduleID}/students")
def list_module_students(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    results = db.execute(
        select(Student).join(Enrollment, Enrollment.studentID == Student.studentID)
        .where(Enrollment.moduleID == moduleID)
    ).scalars().all()

    return [{"studentID": s.studentID, "studentNumber": s.studentNumber, "fullName": s.fullName} for s in results]