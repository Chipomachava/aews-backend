from pydantic import BaseModel


class StudentBase(BaseModel):
    studentNumber: str
    fullName: str


class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    studentID: int

    class Config:
        from_attributes = True