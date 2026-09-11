import sys
import os
sys.path.append(os.getcwd())

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.student import Student
from app.models.module import Module
from app.models.enrollment import Enrollment
from app.models.academic_indicator import AcademicIndicator
from app.services.csv_validator import validate_csv


@pytest.fixture
def test_db():
    """Creates a fresh in-memory SQLite database for each test, seeded with known data."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    module = Module(moduleCode="TESTMOD", moduleName="Test Module")
    db.add(module)
    db.commit()
    db.refresh(module)

    student = Student(studentNumber="1234567", fullName="Test Student")
    db.add(student)
    db.commit()
    db.refresh(student)

    enrollment = Enrollment(studentID=student.studentID, moduleID=module.moduleID)
    db.add(enrollment)

    indicator = AcademicIndicator(
        name="TestMark", dataType="Percentage", minValue=0, maxValue=100,
        isActive=True, higherIsBetter=True,
    )
    db.add(indicator)
    db.commit()

    yield db, module.moduleID, student.studentNumber

    db.close()


def test_valid_csv_passes(test_db):
    db, moduleID, studentNumber = test_db
    csv_content = f"studentNumber,TestMark\n{studentNumber},75.0\n".encode()

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is True
    assert len(errors) == 0
    assert len(parsed_rows) == 1
    assert parsed_rows[0]["rawValue"] == 75.0


def test_unknown_student_is_rejected(test_db):
    db, moduleID, _ = test_db
    csv_content = b"studentNumber,TestMark\n9999999,75.0\n"

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is False
    assert any("not found" in e for e in errors)


def test_out_of_range_value_is_rejected(test_db):
    db, moduleID, studentNumber = test_db
    csv_content = f"studentNumber,TestMark\n{studentNumber},150.0\n".encode()

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is False
    assert any("outside allowed range" in e for e in errors)


def test_missing_student_number_column_is_rejected(test_db):
    db, moduleID, _ = test_db
    csv_content = b"wrongColumn,TestMark\n1234567,75.0\n"

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is False
    assert any("studentNumber" in e for e in errors)


def test_non_numeric_value_is_rejected(test_db):
    db, moduleID, studentNumber = test_db
    csv_content = f"studentNumber,TestMark\n{studentNumber},notanumber\n".encode()

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is False
    assert any("not a valid number" in e for e in errors)


def test_unenrolled_student_is_rejected(test_db):
    db, moduleID, studentNumber = test_db

    other_student = Student(studentNumber="7654321", fullName="Not Enrolled Student")
    db.add(other_student)
    db.commit()

    csv_content = b"studentNumber,TestMark\n7654321,75.0\n"

    is_valid, errors, parsed_rows = validate_csv(csv_content, moduleID, db)

    assert is_valid is False
    assert any("not enrolled" in e for e in errors)