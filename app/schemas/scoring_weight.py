from pydantic import BaseModel, field_validator
from datetime import datetime


class ScoringWeightBase(BaseModel):
    indicatorID: int
    weightValue: float

    @field_validator("weightValue")
    @classmethod
    def weight_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("weightValue must be non-negative")
        return v


class ScoringWeightCreate(ScoringWeightBase):
    pass


class ScoringWeightResponse(ScoringWeightBase):
    weightID: int
    updatedBy: int
    updatedAt: datetime

    class Config:
        from_attributes = True