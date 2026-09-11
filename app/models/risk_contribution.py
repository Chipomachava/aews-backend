from sqlalchemy import Column, Integer, Float, ForeignKey
from app.database import Base


class RiskContribution(Base):
    __tablename__ = "risk_contributions"

    contributionID = Column(Integer, primary_key=True, index=True)
    riskScoreID = Column(Integer, ForeignKey("risk_scores.riskScoreID"), nullable=False)
    indicatorID = Column(Integer, ForeignKey("academic_indicators.indicatorID"), nullable=False)
    rawValue = Column(Float, nullable=False)
    weightApplied = Column(Float, nullable=False)
    weightedContribution = Column(Float, nullable=False)  # = rawValue × weightApplied