from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InterventionNote(Base):
    __tablename__ = "intervention_notes"

    interventionID = Column(Integer, primary_key=True, index=True)
    studentID = Column(Integer, ForeignKey("students.studentID"), nullable=False)
    lecturerID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    interventionType = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    followUpDate = Column(Date, nullable=True)
    contextNote = Column(Text, nullable=True)
    riskLabelAtTime = Column(String(10), nullable=False)  # snapshot at time of intervention
    status = Column(String(20), nullable=False, default="Open")  # Open / Resolved
    outcomeNote = Column(Text, nullable=True)
    resolvedBy = Column(Integer, ForeignKey("users.userID"), nullable=True)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    resolvedAt = Column(DateTime(timezone=True), nullable=True)

    # Lets the API show "2022114455 - T.N." instead of "Student 17".
    # lazy="joined" fetches the student in the same query, so the list page
    # does not fire one extra query per intervention.
    student = relationship("Student", lazy="joined")

    @property
    def studentNumber(self) -> str:
        return self.student.studentNumber if self.student else ""

    @property
    def studentInitials(self) -> str:
        """'Thabo Nkosi' -> 'T.N.' - identifies the student without naming them."""
        if not self.student or not self.student.fullName:
            return ""
        parts = [p for p in self.student.fullName.split() if p]
        return ".".join(p[0].upper() for p in parts) + "." if parts else ""