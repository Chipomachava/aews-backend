from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.csv_upload import CSVUpload
from app.models.risk_score import RiskScore
from app.models.risk_contribution import RiskContribution
from app.models.academic_indicator import AcademicIndicator
from app.models.student import Student
from app.schemas.risk_score import RiskScoreResponse
from app.schemas.risk_contribution import RiskContributionResponse
from app.services.dependencies import require_role, get_current_user
from app.services.scoring_engine import compute_risk_scores
from app.models.module import Module
from app.models.lecturer_module import LecturerModule
from app.models.enrollment import Enrollment
from app.models.intervention_note import InterventionNote

router = APIRouter(prefix="/risk-scores", tags=["Risk Scores"])


@router.post("/compute/{uploadID}")
def compute_scores(
    uploadID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin", "Lecturer")),
):
    upload = db.get(CSVUpload, uploadID)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    if upload.status != "Success":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot score a failed upload")

    try:
        results = compute_risk_scores(uploadID=uploadID, moduleID=upload.moduleID, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"uploadID": uploadID, "studentsScored": len(results), "results": results}


@router.get("/module/{moduleID}", response_model=list[RiskScoreResponse])
def get_module_risk_scores(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    return db.execute(
        select(RiskScore).where(RiskScore.moduleID == moduleID).order_by(RiskScore.totalScore.desc())
    ).scalars().all()


@router.get("/{riskScoreID}/breakdown", response_model=list[RiskContributionResponse])
def get_score_breakdown(
    riskScoreID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    risk_score = db.get(RiskScore, riskScoreID)
    if not risk_score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk score not found")

    return db.execute(
        select(RiskContribution).where(RiskContribution.riskScoreID == riskScoreID)
    ).scalars().all()


@router.get("/module/{moduleID}/full")
def get_full_module_analysis(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    all_scores = db.execute(
        select(RiskScore).where(RiskScore.moduleID == moduleID)
    ).scalars().all()

    latest_by_student = {}
    for rs in all_scores:
        existing = latest_by_student.get(rs.studentID)
        if not existing or rs.computedAt > existing.computedAt:
            latest_by_student[rs.studentID] = rs

    indicators = db.execute(select(AcademicIndicator)).scalars().all()
    indicator_name_by_id = {ind.indicatorID: ind.name for ind in indicators}

    results = []
    for studentID, rs in latest_by_student.items():
        student = db.get(Student, studentID)
        contributions = db.execute(
            select(RiskContribution).where(RiskContribution.riskScoreID == rs.riskScoreID)
        ).scalars().all()

        indicator_values = {}
        for c in contributions:
            name = indicator_name_by_id.get(c.indicatorID, f"Indicator {c.indicatorID}")
            indicator_values[name] = c.rawValue

        results.append({
            "studentID": studentID,
            "studentNumber": student.studentNumber if student else None,
            "fullName": student.fullName if student else None,
            "riskScoreID": rs.riskScoreID,
            "totalScore": rs.totalScore,
            "riskLabel": rs.riskLabel,
            "isPartial": rs.isPartial,
            "computedAt": rs.computedAt,
            "indicatorValues": indicator_values,
        })

    results.sort(key=lambda r: r["totalScore"], reverse=True)

    used_indicator_names = set()
    for r in results:
        used_indicator_names.update(r["indicatorValues"].keys())

    ordered_names = [name for name in indicator_name_by_id.values() if name in used_indicator_names]

    return {
        "indicatorNames": ordered_names,
        "students": results,
    }


@router.get("/module/{moduleID}/top-driver")
def get_top_risk_driver(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.dependencies import verify_module_access
    verify_module_access(moduleID, current_user, db)

    all_scores = db.execute(
        select(RiskScore).where(RiskScore.moduleID == moduleID)
    ).scalars().all()

    latest_by_student = {}
    for rs in all_scores:
        existing = latest_by_student.get(rs.studentID)
        if not existing or rs.computedAt > existing.computedAt:
            latest_by_student[rs.studentID] = rs

    at_risk_score_ids = [
        rs.riskScoreID for rs in latest_by_student.values()
        if rs.riskLabel in ("High", "Medium")
    ]

    if not at_risk_score_ids:
        return {"indicatorName": None, "percentage": 0, "atRiskCount": 0}

    contributions = db.execute(
        select(RiskContribution).where(RiskContribution.riskScoreID.in_(at_risk_score_ids))
    ).scalars().all()

    totals: dict[int, float] = {}
    grand_total = 0.0
    for c in contributions:
        totals[c.indicatorID] = totals.get(c.indicatorID, 0.0) + c.weightedContribution
        grand_total += c.weightedContribution

    if grand_total <= 0 or not totals:
        return {"indicatorName": None, "percentage": 0, "atRiskCount": len(at_risk_score_ids)}

    top_indicator_id = max(totals, key=totals.get)
    percentage = round((totals[top_indicator_id] / grand_total) * 100, 1)

    return {
        "indicatorName": indicator_name_by_id.get(top_indicator_id, f"Indicator {top_indicator_id}") if (indicator_name_by_id := {ind.indicatorID: ind.name for ind in db.execute(select(AcademicIndicator)).scalars().all()}) else None,
        "percentage": percentage,
        "atRiskCount": len(at_risk_score_ids),
    }
@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "Admin":
        modules = db.execute(select(Module)).scalars().all()
    else:
        module_ids = db.execute(
            select(LecturerModule.moduleID).where(LecturerModule.lecturerID == current_user.userID)
        ).scalars().all()
        modules = db.execute(select(Module).where(Module.moduleID.in_(module_ids))).scalars().all() if module_ids else []

    module_summaries = []
    total_high = total_medium = total_low = total_students = 0

    for module in modules:
        all_scores = db.execute(select(RiskScore).where(RiskScore.moduleID == module.moduleID)).scalars().all()
        latest_by_student = {}
        for rs in all_scores:
            existing = latest_by_student.get(rs.studentID)
            if not existing or rs.computedAt > existing.computedAt:
                latest_by_student[rs.studentID] = rs
        scores = list(latest_by_student.values())
        high = len([s for s in scores if s.riskLabel == "High"])
        medium = len([s for s in scores if s.riskLabel == "Medium"])
        low = len([s for s in scores if s.riskLabel == "Low"])

        module_summaries.append({
            "moduleID": module.moduleID,
            "moduleCode": module.moduleCode,
            "moduleName": module.moduleName,
            "totalStudents": len(scores),
            "high": high,
            "medium": medium,
            "low": low,
        })
        total_high += high
        total_medium += medium
        total_low += low
        total_students += len(scores)

    module_ids_list = [m.moduleID for m in modules]

    if current_user.role.value == "Admin":
        all_interventions = db.execute(select(InterventionNote)).scalars().all()
    else:
        my_student_ids = db.execute(
            select(Enrollment.studentID).where(Enrollment.moduleID.in_(module_ids_list))
        ).scalars().all() if module_ids_list else []
        all_interventions = db.execute(
            select(InterventionNote).where(InterventionNote.studentID.in_(my_student_ids))
        ).scalars().all() if my_student_ids else []

    open_interventions = [iv for iv in all_interventions if iv.status == "Open"]
    recent_interventions = sorted(all_interventions, key=lambda x: x.createdAt, reverse=True)[:5]

    recent_uploads = []
    if module_ids_list:
        recent_uploads = db.execute(
            select(CSVUpload)
            .where(CSVUpload.moduleID.in_(module_ids_list), CSVUpload.status == "Success")
            .order_by(CSVUpload.uploadedAt.desc())
            .limit(5)
        ).scalars().all()

    students_with_open_intervention = {iv.studentID for iv in open_interventions}
    needs_attention = 0
    for module in modules:
        all_scores = db.execute(select(RiskScore).where(RiskScore.moduleID == module.moduleID)).scalars().all()
        latest_by_student = {}
        for rs in all_scores:
            existing = latest_by_student.get(rs.studentID)
            if not existing or rs.computedAt > existing.computedAt:
                latest_by_student[rs.studentID] = rs
        for rs in latest_by_student.values():
            if rs.riskLabel == "High" and rs.studentID not in students_with_open_intervention:
                needs_attention += 1

    return {
        "totals": {
            "modules": len(modules),
            "students": total_students,
            "high": total_high,
            "medium": total_medium,
            "low": total_low,
            "openInterventions": len(open_interventions),
            "needsAttention": needs_attention,
        },
        "modules": module_summaries,
        "recentUploads": [
            {"uploadID": u.uploadID, "fileName": u.fileName, "moduleID": u.moduleID, "recordCount": u.recordCount, "uploadedAt": u.uploadedAt}
            for u in recent_uploads
        ],
        "recentInterventions": [
            {"interventionID": iv.interventionID, "studentID": iv.studentID, "interventionType": iv.interventionType, "status": iv.status, "createdAt": iv.createdAt}
            for iv in recent_interventions
        ],
    }