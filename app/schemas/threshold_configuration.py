from pydantic import BaseModel, model_validator
from datetime import datetime


class ThresholdConfigurationBase(BaseModel):
    lowMax: float
    mediumMax: float

    @model_validator(mode="after")
    def medium_must_exceed_low(self):
        if self.mediumMax <= self.lowMax:
            raise ValueError("mediumMax must be greater than lowMax")
        return self


class ThresholdConfigurationCreate(ThresholdConfigurationBase):
    pass


class ThresholdConfigurationResponse(ThresholdConfigurationBase):
    thresholdID: int
    updatedBy: int
    updatedAt: datetime

    class Config:
        from_attributes = True