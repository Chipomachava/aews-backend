from pydantic import BaseModel


class RiskContributionResponse(BaseModel):
    contributionID: int
    riskScoreID: int
    indicatorID: int
    rawValue: float
    weightApplied: float
    weightedContribution: float

    class Config:
        from_attributes = True