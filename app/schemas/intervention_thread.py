from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.schemas.intervention_note import InterventionNoteResponse


class AttachmentInfo(BaseModel):
    attachmentID: int
    interventionID: int
    replyID: Optional[int] = None
    fileName: str
    fileType: str
    fileSize: int
    sentToStudent: bool = False
    uploadedBy: int
    uploadedAt: datetime

    class Config:
        from_attributes = True


class ReplyInfo(BaseModel):
    replyID: int
    interventionID: int
    authorID: int
    authorName: str
    message: str
    channel: Optional[str] = None
    createdAt: datetime
    attachments: List[AttachmentInfo] = []


class ThreadResponse(BaseModel):
    intervention: InterventionNoteResponse
    lecturerName: str
    canReply: bool
    attachments: List[AttachmentInfo] = []
    replies: List[ReplyInfo] = []