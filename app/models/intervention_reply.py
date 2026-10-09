from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class InterventionReply(Base):
    __tablename__ = "intervention_replies"

    replyID = Column(Integer, primary_key=True, index=True)
    interventionID = Column(
        Integer,
        ForeignKey("intervention_notes.interventionID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(20), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())