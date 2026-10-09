import os
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session, defer
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.risk_score import RiskScore
from app.models.intervention_note import InterventionNote
from app.models.intervention_reply import InterventionReply
from app.models.intervention_attachment import InterventionAttachment
from app.models.lecturer_module import LecturerModule
from app.models.enrollment import Enrollment
from app.schemas.intervention_note import (
    InterventionNoteCreate,
    InterventionNoteResolve,
    InterventionNoteResponse,
)
from app.schemas.intervention_thread import AttachmentInfo, ReplyInfo, ThreadResponse
from app.services.audit_service import log_event
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/interventions", tags=["Interventions"])

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 5
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}


def _get_intervention_or_404(db: Session, interventionID: int) -> InterventionNote:
    intervention = db.get(InterventionNote, interventionID)
    if not intervention:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")
    return intervention


def _can_write(user: User, intervention: InterventionNote) -> bool:
    return user.role.value == "Admin" or intervention.lecturerID == user.userID


def _can_view(db: Session, user: User, intervention: InterventionNote) -> bool:
    if _can_write(user, intervention):
        return True

    my_module_ids = db.execute(
        select(LecturerModule.moduleID).where(LecturerModule.lecturerID == user.userID)
    ).scalars().all()
    if not my_module_ids:
        return False

    match = db.execute(
        select(Enrollment.studentID).where(
            Enrollment.studentID == intervention.studentID,
            Enrollment.moduleID.in_(my_module_ids),
        )
    ).first()
    return match is not None


def _require_view(db: Session, user: User, intervention: InterventionNote):
    if not _can_view(db, user, intervention):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this intervention")


def _require_write(user: User, intervention: InterventionNote):
    if not _can_write(user, intervention):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lecturer who created this intervention can add to it",
        )


def _read_valid_files(files: Optional[List[UploadFile]]) -> list:
    real_files = [f for f in (files or []) if f and f.filename]

    if len(real_files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can attach at most {MAX_FILES_PER_UPLOAD} files at a time",
        )

    checked = []
    for f in real_files:
        name = os.path.basename(f.filename)[:255]
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{ext or 'unknown'}' is not allowed ({name})",
            )
        data = f.file.read(MAX_FILE_BYTES + 1)
        if len(data) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{name} is empty")
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{name} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB",
            )
        checked.append((name, f.content_type or "application/octet-stream", data))
    return checked


def _store_files(
    db: Session,
    checked: list,
    interventionID: int,
    replyID: Optional[int],
    user: User,
    sent_to_student: bool = False,
) -> list:
    saved = []
    for name, ftype, data in checked:
        attachment = InterventionAttachment(
            interventionID=interventionID,
            replyID=replyID,
            fileName=name,
            fileType=ftype,
            fileSize=len(data),
            fileData=data,
            sentToStudent=sent_to_student,
            uploadedBy=user.userID,
        )
        db.add(attachment)
        saved.append(attachment)
    db.flush()
    return saved


@router.post("/", response_model=InterventionNoteResponse, status_code=status.HTTP_201_CREATED)
def record_intervention(
    intervention_in: InterventionNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    latest_score = db.execute(
        select(RiskScore)
        .where(RiskScore.studentID == intervention_in.studentID)
        .order_by(RiskScore.computedAt.desc())
    ).scalars().first()

    risk_label_at_time = latest_score.riskLabel if latest_score else "Unknown"

    new_intervention = InterventionNote(
        studentID=intervention_in.studentID,
        lecturerID=current_user.userID,
        interventionType=intervention_in.interventionType,
        description=intervention_in.description,
        followUpDate=intervention_in.followUpDate,
        contextNote=intervention_in.contextNote,
        riskLabelAtTime=risk_label_at_time,
        status="Open",
    )
    db.add(new_intervention)
    db.commit()
    db.refresh(new_intervention)
    return new_intervention


@router.get("/", response_model=list[InterventionNoteResponse])
def list_interventions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "Admin":
        return db.execute(select(InterventionNote)).scalars().all()

    my_module_ids = db.execute(
        select(LecturerModule.moduleID).where(LecturerModule.lecturerID == current_user.userID)
    ).scalars().all()

    if not my_module_ids:
        return []

    my_student_ids = db.execute(
        select(Enrollment.studentID).where(Enrollment.moduleID.in_(my_module_ids))
    ).scalars().all()

    return db.execute(
        select(InterventionNote).where(InterventionNote.studentID.in_(my_student_ids))
    ).scalars().all()


@router.patch("/{interventionID}/resolve", response_model=InterventionNoteResponse)
def resolve_intervention(
    interventionID: int,
    resolve_in: InterventionNoteResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = db.get(InterventionNote, interventionID)
    if not intervention:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")

    if intervention.status == "Resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Intervention already resolved")

    intervention.status = "Resolved"
    intervention.outcomeNote = resolve_in.outcomeNote
    intervention.resolvedBy = current_user.userID
    intervention.resolvedAt = datetime.now(timezone.utc)

    db.commit()
    db.refresh(intervention)
    return intervention


@router.post("/{interventionID}/notify")
def notify_student(
    interventionID: int,
    channel: str = Form(...),
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = _get_intervention_or_404(db, interventionID)
    _require_write(current_user, intervention)

    message = message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    checked = _read_valid_files(files)

    from app.models.student import Student
    student = db.get(Student, intervention.studentID)

    record = InterventionReply(
        interventionID=interventionID,
        authorID=current_user.userID,
        message=message,
        channel=channel,
    )
    db.add(record)
    db.flush()
    saved = _store_files(db, checked, interventionID, record.replyID, current_user, sent_to_student=True)
    db.commit()

    sent_note = f" with {len(saved)} resource(s): {', '.join(a.fileName for a in saved)}" if saved else ""
    log_event(
        db,
        eventType="NOTIFICATION_SIMULATED",
        description=f"{channel} notification (simulated) to {student.fullName if student else 'student'}{sent_note}: \"{message}\"",
        userID=current_user.userID,
        targetEntity="InterventionNote",
        targetID=interventionID,
    )

    return {
        "message": "Sent successfully",
        "attachments": [AttachmentInfo.model_validate(a).model_dump(mode="json") for a in saved],
    }


@router.get("/{interventionID}/thread", response_model=ThreadResponse)
def get_thread(
    interventionID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = _get_intervention_or_404(db, interventionID)
    _require_view(db, current_user, intervention)

    replies = db.execute(
        select(InterventionReply)
        .where(InterventionReply.interventionID == interventionID)
        .order_by(InterventionReply.createdAt, InterventionReply.replyID)
    ).scalars().all()

    attachments = db.execute(
        select(InterventionAttachment)
        .options(defer(InterventionAttachment.fileData))
        .where(InterventionAttachment.interventionID == interventionID)
        .order_by(InterventionAttachment.uploadedAt, InterventionAttachment.attachmentID)
    ).scalars().all()

    user_ids = {r.authorID for r in replies} | {intervention.lecturerID}
    names = {
        u.userID: u.fullName
        for u in db.execute(select(User).where(User.userID.in_(user_ids))).scalars().all()
    }

    by_reply: dict = {}
    on_intervention = []
    for a in attachments:
        info = AttachmentInfo.model_validate(a)
        if a.replyID is None:
            on_intervention.append(info)
        else:
            by_reply.setdefault(a.replyID, []).append(info)

    return ThreadResponse(
        intervention=InterventionNoteResponse.model_validate(intervention),
        lecturerName=names.get(intervention.lecturerID, "Unknown"),
        canReply=_can_write(current_user, intervention),
        attachments=on_intervention,
        replies=[
            ReplyInfo(
                replyID=r.replyID,
                interventionID=r.interventionID,
                authorID=r.authorID,
                authorName=names.get(r.authorID, "Unknown"),
                message=r.message,
                channel=r.channel,
                createdAt=r.createdAt,
                attachments=by_reply.get(r.replyID, []),
            )
            for r in replies
        ],
    )


@router.post("/{interventionID}/replies", response_model=ReplyInfo, status_code=status.HTTP_201_CREATED)
def add_reply(
    interventionID: int,
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = _get_intervention_or_404(db, interventionID)
    _require_write(current_user, intervention)

    message = message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reply message cannot be empty")

    checked = _read_valid_files(files)

    reply = InterventionReply(
        interventionID=interventionID,
        authorID=current_user.userID,
        message=message,
    )
    db.add(reply)
    db.flush()
    saved = _store_files(db, checked, interventionID, reply.replyID, current_user)
    db.commit()
    db.refresh(reply)

    log_event(
        db,
        eventType="INTERVENTION_REPLY_ADDED",
        description=f"Follow-up added to intervention #{interventionID} with {len(saved)} attachment(s)",
        userID=current_user.userID,
        targetEntity="InterventionNote",
        targetID=interventionID,
    )

    return ReplyInfo(
        replyID=reply.replyID,
        interventionID=reply.interventionID,
        authorID=reply.authorID,
        authorName=current_user.fullName,
        message=reply.message,
        channel=reply.channel,
        createdAt=reply.createdAt,
        attachments=[AttachmentInfo.model_validate(a) for a in saved],
    )


@router.post("/{interventionID}/attachments", response_model=List[AttachmentInfo], status_code=status.HTTP_201_CREATED)
def add_attachments(
    interventionID: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    intervention = _get_intervention_or_404(db, interventionID)
    _require_write(current_user, intervention)

    checked = _read_valid_files(files)
    if not checked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file was provided")

    saved = _store_files(db, checked, interventionID, None, current_user)
    db.commit()

    log_event(
        db,
        eventType="INTERVENTION_FILE_ATTACHED",
        description=f"{len(saved)} file(s) attached to intervention #{interventionID}",
        userID=current_user.userID,
        targetEntity="InterventionNote",
        targetID=interventionID,
    )

    return [AttachmentInfo.model_validate(a) for a in saved]


@router.get("/attachments/{attachmentID}/download")
def download_attachment(
    attachmentID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    attachment = db.get(InterventionAttachment, attachmentID)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    intervention = _get_intervention_or_404(db, attachment.interventionID)
    _require_view(db, current_user, intervention)

    return Response(
        content=bytes(attachment.fileData),
        media_type=attachment.fileType,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.fileName)}",
        },
    )


@router.delete("/attachments/{attachmentID}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachmentID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    attachment = db.get(InterventionAttachment, attachmentID)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    intervention = _get_intervention_or_404(db, attachment.interventionID)
    _require_write(current_user, intervention)

    file_name = attachment.fileName
    db.delete(attachment)
    db.commit()

    log_event(
        db,
        eventType="INTERVENTION_FILE_DELETED",
        description=f"File '{file_name}' removed from intervention #{intervention.interventionID}",
        userID=current_user.userID,
        targetEntity="InterventionNote",
        targetID=intervention.interventionID,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)