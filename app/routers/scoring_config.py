from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.scoring_weight import ScoringWeight
from app.models.threshold_configuration import ThresholdConfiguration
from app.schemas.scoring_weight import ScoringWeightCreate, ScoringWeightResponse
from app.schemas.threshold_configuration import ThresholdConfigurationCreate, ThresholdConfigurationResponse
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/scoring-config", tags=["Scoring Configuration"])


@router.post("/weights", response_model=ScoringWeightResponse, status_code=status.HTTP_201_CREATED)
def set_weight(
    weight_in: ScoringWeightCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    existing = db.execute(
        select(ScoringWeight).where(ScoringWeight.indicatorID == weight_in.indicatorID)
    ).scalar_one_or_none()

    if existing:
        old_value = existing.weightValue
        existing.weightValue = weight_in.weightValue
        existing.updatedBy = current_user.userID
        db.commit()
        db.refresh(existing)

        from app.services.audit_service import log_event
        from app.services.config_history_service import log_config_change

        log_event(db, eventType="CONFIG_CHANGE", description=f"Weight updated for indicator {existing.indicatorID}", userID=current_user.userID, targetEntity="ScoringWeight", targetID=existing.weightID)
        log_config_change(db, configType="Weight", referenceID=existing.weightID, oldValue=old_value, newValue=existing.weightValue, changedBy=current_user.userID)

        return existing

        from app.services.audit_service import log_event
        log_event(db, eventType="CONFIG_CHANGE", description=f"Weight updated for indicator {existing.indicatorID}", userID=current_user.userID, targetEntity="ScoringWeight", targetID=existing.weightID)

        return existing

    new_weight = ScoringWeight(
        indicatorID=weight_in.indicatorID,
        weightValue=weight_in.weightValue,
        updatedBy=current_user.userID,
    )
    db.add(new_weight)
    db.commit()
    db.refresh(new_weight)
    return new_weight


@router.get("/weights", response_model=list[ScoringWeightResponse])
def list_weights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(select(ScoringWeight)).scalars().all()


@router.post("/thresholds", response_model=ThresholdConfigurationResponse, status_code=status.HTTP_201_CREATED)
def set_thresholds(
    threshold_in: ThresholdConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    new_threshold = ThresholdConfiguration(
        lowMax=threshold_in.lowMax,
        mediumMax=threshold_in.mediumMax,
        updatedBy=current_user.userID,
    )
    db.add(new_threshold)
    db.commit()
    db.refresh(new_threshold)

    from app.services.config_history_service import log_config_change
    log_config_change(
        db,
        configType="Threshold",
        referenceID=new_threshold.thresholdID,
        oldValue="N/A (new configuration)",
        newValue=f"low<={new_threshold.lowMax}, medium<={new_threshold.mediumMax}",
        changedBy=current_user.userID,
    )

    return new_threshold

@router.get("/thresholds", response_model=list[ThresholdConfigurationResponse])
def list_thresholds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(select(ThresholdConfiguration)).scalars().all()