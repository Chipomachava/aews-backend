from sqlalchemy.orm import Session
from app.models.configuration_history import ConfigurationHistory


def log_config_change(
    db: Session,
    configType: str,
    referenceID: int,
    oldValue: str,
    newValue: str,
    changedBy: int,
):
    entry = ConfigurationHistory(
        configType=configType,
        referenceID=referenceID,
        oldValue=str(oldValue),
        newValue=str(newValue),
        changedBy=changedBy,
    )
    db.add(entry)
    db.commit()