from app.database import SessionLocal
from app.models.academic_indicator import AcademicIndicator
from app.models.scoring_weight import ScoringWeight
from app.models.user import User

db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@aews.ac.za").first()
admin_id = admin.userID if admin else None

CANONICAL_INDICATORS = [
    {"name": "AssessmentPerformance", "weight": 0.40},
    {"name": "TestPerformance", "weight": 0.35},
    {"name": "AttendanceEngagement", "weight": 0.25},
]

for item in CANONICAL_INDICATORS:
    existing = db.query(AcademicIndicator).filter(AcademicIndicator.name == item["name"]).first()

    if existing:
        print(f"{item['name']} already exists (indicatorID={existing.indicatorID}) - skipping.")
        continue

    indicator = AcademicIndicator(
        name=item["name"],
        dataType="Percentage",
        minValue=0.0,
        maxValue=100.0,
        isActive=True,
        higherIsBetter=True,
    )
    db.add(indicator)
    db.flush()  # so indicator.indicatorID is populated before we use it below

    weight = ScoringWeight(
        indicatorID=indicator.indicatorID,
        weightValue=item["weight"],
        updatedBy=admin_id,
    )
    db.add(weight)

    print(f"Created {item['name']} (indicatorID={indicator.indicatorID}) with weight {item['weight']}")

db.commit()
db.close()