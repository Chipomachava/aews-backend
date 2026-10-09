from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func, false
from app.database import Base


class InterventionAttachment(Base):
    """
    A file (PDF, image, Word document, etc.) attached to an intervention
    or to one of its replies. The file bytes are stored in the database
    so nothing depends on Render's disk, which is wiped on every deploy.
    """
    __tablename__ = "intervention_attachments"

    attachmentID = Column(Integer, primary_key=True, index=True)
    interventionID = Column(
        Integer,
        ForeignKey("intervention_notes.interventionID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NULL = attached to the intervention itself; set = attached to a reply
    replyID = Column(
        Integer,
        ForeignKey("intervention_replies.replyID", ondelete="CASCADE"),
        nullable=True,
    )
    fileName = Column(String(255), nullable=False)
    fileType = Column(String(100), nullable=False)   # MIME type, e.g. application/pdf
    fileSize = Column(Integer, nullable=False)       # bytes
    fileData = Column(LargeBinary, nullable=False)
    # True = resource sent to the student with a notification.
    # False = lecturer's own working file, kept on the record only.
    sentToStudent = Column(Boolean, nullable=False, server_default=false())
    uploadedBy = Column(Integer, ForeignKey("users.userID"), nullable=False)
    uploadedAt = Column(DateTime(timezone=True), server_default=func.now())