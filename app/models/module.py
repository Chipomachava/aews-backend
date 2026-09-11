from sqlalchemy import Column, Integer, String
from app.database import Base


class Module(Base):
    __tablename__ = "modules"

    moduleID = Column(Integer, primary_key=True, index=True)
    moduleCode = Column(String(20), unique=True, nullable=False, index=True)
    moduleName = Column(String(150), nullable=False)