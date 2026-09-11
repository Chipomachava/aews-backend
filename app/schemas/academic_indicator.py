from pydantic import BaseModel


class AcademicIndicatorBase(BaseModel):
    name: str
    dataType: str
    minValue: float
    maxValue: float
    isActive: bool = True
    higherIsBetter: bool = True


class AcademicIndicatorCreate(AcademicIndicatorBase):
    pass


class AcademicIndicatorResponse(AcademicIndicatorBase):
    indicatorID: int

    class Config:
        from_attributes = True