from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.module import Module
from app.schemas.module import ModuleCreate, ModuleResponse
from app.services.dependencies import require_role, get_current_user

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.post("/", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    module_in: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    existing = db.execute(select(Module).where(Module.moduleCode == module_in.moduleCode)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module code already exists")

    new_module = Module(moduleCode=module_in.moduleCode, moduleName=module_in.moduleName)
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module


@router.get("/", response_model=list[ModuleResponse])
def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(select(Module)).scalars().all()
@router.patch("/{moduleID}", response_model=ModuleResponse)
def update_module(
    moduleID: int,
    module_in: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    module.moduleCode = module_in.moduleCode
    module.moduleName = module_in.moduleName
    db.commit()
    db.refresh(module)
    return module


@router.delete("/{moduleID}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    moduleID: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("Admin")),
):
    module = db.get(Module, moduleID)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    db.delete(module)
    db.commit()