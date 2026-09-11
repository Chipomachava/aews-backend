from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
import pandas as pd

from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.module import Module
from app.models.enrollment import Enrollment
from app.schemas.student import StudentCreate, StudentResponse
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    existing = db.execute(select(Student).where(Student.studentNumber == student_in.studentNumber)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student number already exists")

    new_student = Student(studentNumber=student_in.studentNumber, fullName=student_in.fullName)
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


@router.get("/", response_model=list[StudentResponse])
def list_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(select(Student)).scalars().all()


@router.patch("/{studentID}", response_model=StudentResponse)
def update_student(
    studentID: int,
    student_in: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    student = db.get(Student, studentID)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    student.studentNumber = student_in.studentNumber
    student.fullName = student_in.fullName
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{studentID}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    studentID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    student = db.get(Student, studentID)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    from app.models.risk_contribution import RiskContribution
    from app.models.risk_score import RiskScore
    from app.models.intervention_note import InterventionNote
    from app.models.academic_record import AcademicRecord

    risk_score_ids = db.execute(
        select(RiskScore.riskScoreID).where(RiskScore.studentID == studentID)
    ).scalars().all()

    if risk_score_ids:
        db.execute(RiskContribution.__table__.delete().where(RiskContribution.riskScoreID.in_(risk_score_ids)))

    db.execute(RiskScore.__table__.delete().where(RiskScore.studentID == studentID))
    db.execute(InterventionNote.__table__.delete().where(InterventionNote.studentID == studentID))
    db.execute(AcademicRecord.__table__.delete().where(AcademicRecord.studentID == studentID))
    db.execute(Enrollment.__table__.delete().where(Enrollment.studentID == studentID))

    db.delete(student)
    db.commit()

    from app.services.audit_service import log_event
    log_event(db, eventType="STUDENT_DELETED", description=f"Student {student.studentNumber} ({student.fullName}) deleted", userID=current_user.userID, targetEntity="Student", targetID=studentID)


@router.post("/bulk-upload/{moduleID}")
async def bulk_upload_students(
    moduleID: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    file_bytes = await file.read()

    try:
        df = pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype={"studentNumber": str})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not read CSV: {str(e)}")

    required_columns = {"studentNumber", "fullName"}
    if not required_columns.issubset(df.columns):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must contain 'studentNumber' and 'fullName' columns",
        )

    created_count = 0
    enrolled_count = 0
    already_enrolled_count = 0
    errors = []

    for row_num, row in df.iterrows():
        student_number = str(row["studentNumber"]).strip()
        full_name = str(row["fullName"]).strip()

        if not student_number or not full_name:
            errors.append(f"Row {row_num + 2}: missing studentNumber or fullName")
            continue

        student = db.execute(select(Student).where(Student.studentNumber == student_number)).scalar_one_or_none()

        if not student:
            student = Student(studentNumber=student_number, fullName=full_name)
            db.add(student)
            db.flush()
            created_count += 1

        existing_enrollment = db.execute(
            select(Enrollment).where(Enrollment.studentID == student.studentID, Enrollment.moduleID == moduleID)
        ).scalar_one_or_none()

        if existing_enrollment:
            already_enrolled_count += 1
        else:
            db.add(Enrollment(studentID=student.studentID, moduleID=moduleID))
            enrolled_count += 1

    db.commit()

    from app.services.audit_service import log_event
    log_event(
        db,
        eventType="BULK_STUDENT_UPLOAD",
        description=f"Bulk uploaded students to module {moduleID}: {created_count} created, {enrolled_count} enrolled",
        userID=current_user.userID,
        targetEntity="Module",
        targetID=moduleID,
    )

    return {
        "studentsCreated": created_count,
        "studentsEnrolled": enrolled_count,
        "alreadyEnrolled": already_enrolled_count,
        "errors": errors,
    }