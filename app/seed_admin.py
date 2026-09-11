from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

db = SessionLocal()

existing = db.query(User).filter(User.email == "admin@aews.ac.za").first()

if existing:
    print("Admin already exists.")
else:
    admin = User(
        fullName="Chipo Machava",
        email="admin@aews.ac.za",
        passwordHash=hash_password("ChangeMe123!"),
        role=UserRole.Admin,
        status="Active",
    )
    db.add(admin)
    db.commit()
    print("Admin account created successfully.")

db.close()