from pydantic import BaseModel


class AcademicRecordResponse(BaseModel):
    recordID: int
    uploadID: int
    studentID: int
    indicatorID: int
    rawValue: float

    class Config:
        from_attributes = True