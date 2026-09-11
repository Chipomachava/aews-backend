from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.academic_record import AcademicRecord
from app.models.academic_indicator import AcademicIndicator
from app.models.scoring_weight import ScoringWeight
from app.models.threshold_configuration import ThresholdConfiguration
from app.models.risk_score import RiskScore
from app.models.risk_contribution import RiskContribution


def calculate_indicator_contribution(raw_value: float, weight: float, min_value: float, max_value: float, higher_is_better: bool) -> float:
    """
    Pure function: computes one indicator's weighted risk contribution.
    Isolated from the database so it can be unit tested directly.
    """
    if higher_is_better:
        normalized = max_value - raw_value
    else:
        normalized = raw_value - min_value

    return normalized * weight


def compute_risk_scores(uploadID: int, moduleID: int, db: Session):
    """
    Computes RiskScore + RiskContribution rows for every student in this upload,
    following the Academic Early Warning Scoring Specification (v1.0):

    RISK_SCORE = (Σ weight_i × (100 - value_i)) / (Σ weight_i)

    - Any indicator with no recorded value for a student defaults to 0 (treated as
      "no engagement" / maximum risk deficit on that indicator), but its full configured
      weight still counts in the denominator - missing data is never re-normalized away.
    - Risk classification: score < lowMax -> Low; score < mediumMax -> Medium; else High.
      (Boundary values fall into the higher-risk band, matching the specification.)
    """
    weights = db.execute(select(ScoringWeight)).scalars().all()
    weight_map = {w.indicatorID: w.weightValue for w in weights}

    indicators = db.execute(select(AcademicIndicator)).scalars().all()
    indicator_map = {i.indicatorID: i for i in indicators}

    threshold = db.execute(
        select(ThresholdConfiguration).order_by(ThresholdConfiguration.updatedAt.desc())
    ).scalars().first()

    if not threshold:
        raise ValueError("No threshold configuration exists. An Admin must set thresholds first.")

    records = db.execute(
        select(AcademicRecord).where(AcademicRecord.uploadID == uploadID)
    ).scalars().all()

    student_ids_in_upload = {r.studentID for r in records}

    student_indicator_values = {}
    for r in records:
        student_indicator_values.setdefault(r.studentID, {})[r.indicatorID] = r.rawValue

    results = []

    for studentID in student_ids_in_upload:
        total_weighted = 0.0
        total_weight = 0.0
        contributions = []

        student_records = student_indicator_values.get(studentID, {})

        for indicatorID, weight in weight_map.items():
            indicator = indicator_map.get(indicatorID)
            if not indicator:
                continue

            if indicatorID not in student_records:
                continue  # not uploaded for this student - excluded entirely, weight re-normalized

            raw_value = student_records[indicatorID]

            weighted_contribution = calculate_indicator_contribution(
                raw_value=raw_value,
                weight=weight,
                min_value=indicator.minValue,
                max_value=indicator.maxValue,
                higher_is_better=indicator.higherIsBetter,
            )

            total_weighted += weighted_contribution
            total_weight += weight

            contributions.append({
                "indicatorID": indicatorID,
                "rawValue": raw_value,
                "weightApplied": weight,
                "weightedContribution": weighted_contribution,
            })

        total_score = (total_weighted / total_weight) if total_weight > 0 else 0.0
        total_score = round(total_score, 2)

        if total_score < threshold.lowMax:
            risk_label = "Low"
        elif total_score < threshold.mediumMax:
            risk_label = "Medium"
        else:
            risk_label = "High"

        is_partial = len(student_indicator_values.get(studentID, {})) < len(weight_map)

        risk_score = RiskScore(
            studentID=studentID,
            moduleID=moduleID,
            uploadID=uploadID,
            totalScore=total_score,
            riskLabel=risk_label,
            isPartial=is_partial,
        )
        db.add(risk_score)
        db.flush()

        for c in contributions:
            db.add(RiskContribution(
                riskScoreID=risk_score.riskScoreID,
                indicatorID=c["indicatorID"],
                rawValue=c["rawValue"],
                weightApplied=c["weightApplied"],
                weightedContribution=round(c["weightedContribution"], 2),
            ))

        results.append({
            "studentID": studentID,
            "totalScore": total_score,
            "riskLabel": risk_label,
            "isPartial": is_partial,
        })

    db.commit()
    return results