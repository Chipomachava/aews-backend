import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.academic_indicator import AcademicIndicator

ASSESSMENT_TOKENS = {"assessment", "assessmentperformance", "assignmentmark", "assignment", "assignmentaverage"}
ATTENDANCE_TOKENS = {"attendance", "attendancerate", "attendanceengagement"}


def _match_groups(columns):
    assessment_cols = [c for c in columns if c.lower().replace(" ", "") in ASSESSMENT_TOKENS]
    attendance_cols = [c for c in columns if c.lower().replace(" ", "") in ATTENDANCE_TOKENS]
    test_cols = [c for c in columns if c.lower().startswith("test")]
    return assessment_cols, test_cols, attendance_cols


def validate_csv(file_bytes: bytes, moduleID: int, db: Session):
    """
    Maps raw CSV columns into the three canonical spec indicators:
    - AssessmentPerformance (from Assessment/AssignmentMark columns)
    - TestPerformance (averaged from Test1, Test2, Test3, ... columns)
    - AttendanceEngagement (from Attendance/AttendanceRate columns)

    Per the Risk Scoring Specification:
    - Missing/blank values are treated as 0 (not skipped) - conservative "no engagement" assumption.
    - A canonical category with NO matching columns anywhere in the file is entirely omitted
      (no records created) - the scoring engine treats this as 0 for every student, matching
      the "no assignment data uploaded" scenario in the specification.
    """
    errors = []
    parsed_rows = []

    try:
        df = pd.read_csv(pd.io.common.BytesIO(file_bytes), dtype={"studentNumber": str})
    except Exception as e:
        return False, [f"Could not read CSV file: {str(e)}"], []

    if "studentNumber" not in df.columns:
        return False, ["CSV must contain a 'studentNumber' column"], []

    other_cols = [c for c in df.columns if c != "studentNumber"]
    assessment_cols, test_cols, attendance_cols = _match_groups(other_cols)

    if not assessment_cols and not test_cols and not attendance_cols:
        return False, [
            "CSV must contain at least one recognizable column: Assessment/AssignmentMark, "
            "Test1/Test2/Test3 (or Test), or Attendance/AttendanceRate."
        ], []

    indicators = db.execute(select(AcademicIndicator).where(AcademicIndicator.isActive == True)).scalars().all()
    indicator_map = {ind.name: ind for ind in indicators}

    category_columns = {
        "AssessmentPerformance": assessment_cols,
        "TestPerformance": test_cols,
        "AttendanceEngagement": attendance_cols,
    }

    missing_setup = [name for name, cols in category_columns.items() if cols and name not in indicator_map]
    if missing_setup:
        return False, [
            f"Indicator(s) not configured in Scoring Configuration: {', '.join(missing_setup)}. "
            "Create them (Admin > Scoring Config) with these exact names before uploading."
        ], []

    for row_num, row in df.iterrows():
        student_number = str(row["studentNumber"]).strip()

        student = db.execute(select(Student).where(Student.studentNumber == student_number)).scalar_one_or_none()
        if not student:
            errors.append(f"Row {row_num + 2}: student number '{student_number}' not found")
            continue

        enrolled = db.execute(
            select(Enrollment).where(Enrollment.studentID == student.studentID, Enrollment.moduleID == moduleID)
        ).scalar_one_or_none()
        if not enrolled:
            errors.append(f"Row {row_num + 2}: student '{student_number}' is not enrolled in this module")
            continue

        for canonical_name, cols in category_columns.items():
            if not cols:
                continue

            values = []
            for c in cols:
                raw = row[c]
                if pd.isna(raw) or str(raw).strip() == "":
                    continue
                try:
                    values.append(float(raw))
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num + 2}: '{c}' value '{raw}' is not a valid number (treated as 0)")

            avg_value = sum(values) / len(values) if values else 0.0
            avg_value = max(0.0, min(100.0, avg_value))

            indicator = indicator_map[canonical_name]
            parsed_rows.append({
                "studentID": student.studentID,
                "indicatorID": indicator.indicatorID,
                "rawValue": round(avg_value, 2),
            })

    is_valid = len(parsed_rows) > 0
    return is_valid, errors, parsed_rows