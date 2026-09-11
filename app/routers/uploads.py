import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.module import Module
from app.models.csv_upload import CSVUpload
from app.models.academic_record import AcademicRecord
from app.services.dependencies import require_role, get_current_user
from app.services.csv_validator import validate_csv

router = APIRouter(prefix="/uploads", tags=["CSV Uploads"])


@router.post("/{moduleID}")
async def upload_csv(
    moduleID: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    file_bytes = await file.read()
    checksum = hashlib.sha256(file_bytes).hexdigest()

    duplicate = db.execute(
        select(CSVUpload).where(
            CSVUpload.moduleID == moduleID,
            CSVUpload.checksum == checksum,
            CSVUpload.status == "Success",
        )
    ).scalar_one_or_none()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This exact file was already successfully uploaded (uploadID {duplicate.uploadID}). "
                   f"If you intended to re-upload updated data, please modify the file or confirm this is intentional.",
        )

    is_valid, errors, parsed_rows = validate_csv(file_bytes, moduleID, db)

    upload_record = CSVUpload(
        moduleID=moduleID,
        lecturerID=current_user.userID,
        fileName=file.filename,
        checksum=checksum,
        status="Success" if is_valid else "Failed",
        recordCount=len(parsed_rows) if is_valid else 0,
    )
    db.add(upload_record)
    db.commit()
    db.refresh(upload_record)

    if not is_valid:
        return {
            "uploadID": upload_record.uploadID,
            "status": "Failed",
            "errors": errors,
        }

    for row in parsed_rows:
        record = AcademicRecord(
            uploadID=upload_record.uploadID,
            studentID=row["studentID"],
            indicatorID=row["indicatorID"],
            rawValue=row["rawValue"],
        )
        db.add(record)

    db.commit()

    from app.services.audit_service import log_event
    log_event(
        db,
        eventType="UPLOAD",
        description=f"CSV upload '{file.filename}' processed for module {moduleID}",
        userID=current_user.userID,
        targetEntity="CSVUpload",
        targetID=upload_record.uploadID,
    )

    return {
        "uploadID": upload_record.uploadID,
        "status": "Success",
        "recordsSaved": len(parsed_rows),
    }


@router.get("/module/{moduleID}/latest")
def get_latest_upload(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    latest = db.execute(
        select(CSVUpload)
        .where(CSVUpload.moduleID == moduleID, CSVUpload.status == "Success")
        .order_by(CSVUpload.uploadedAt.desc())
    ).scalars().first()

    if not latest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No successful upload found for this module")

    return {"uploadID": latest.uploadID, "fileName": latest.fileName, "uploadedAt": latest.uploadedAt}


@router.get("/module/{moduleID}/history")
def get_upload_history(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    uploads = db.execute(
        select(CSVUpload)
        .where(CSVUpload.moduleID == moduleID, CSVUpload.status == "Success")
        .order_by(CSVUpload.uploadedAt.desc())
    ).scalars().all()

    return [
        {
            "uploadID": u.uploadID,
            "fileName": u.fileName,
            "status": u.status,
            "recordCount": u.recordCount,
            "uploadedAt": u.uploadedAt,
            "lecturerID": u.lecturerID,
        }
        for u in uploads
    ]


@router.get("/{uploadID}/records")
def get_upload_records(
    uploadID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = db.get(CSVUpload, uploadID)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    from app.services.dependencies import verify_module_access
    verify_module_access(upload.moduleID, current_user, db)

    from app.models.academic_indicator import AcademicIndicator
    from app.models.student import Student

    records = db.execute(select(AcademicRecord).where(AcademicRecord.uploadID == uploadID)).scalars().all()
    indicators = db.execute(select(AcademicIndicator)).scalars().all()
    indicator_name_by_id = {ind.indicatorID: ind.name for ind in indicators}

    by_student: dict[int, dict] = {}
    for r in records:
        if r.studentID not in by_student:
            student = db.get(Student, r.studentID)
            by_student[r.studentID] = {
                "studentID": r.studentID,
                "studentNumber": student.studentNumber if student else None,
                "fullName": student.fullName if student else None,
                "values": {},
            }
        name = indicator_name_by_id.get(r.indicatorID, f"Indicator {r.indicatorID}")
        by_student[r.studentID]["values"][name] = r.rawValue

    return {
        "uploadID": uploadID,
        "fileName": upload.fileName,
        "uploadedAt": upload.uploadedAt,
        "indicatorNames": list(indicator_name_by_id.values()),
        "students": list(by_student.values()),
    }