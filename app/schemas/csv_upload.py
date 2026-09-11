from pydantic import BaseModel
from datetime import datetime


class CSVUploadResponse(BaseModel):
    uploadID: int
    moduleID: int
    lecturerID: int
    fileName: str
    checksum: str
    status: str
    recordCount: int
    uploadedAt: datetime

    class Config:
        from_attributes = True