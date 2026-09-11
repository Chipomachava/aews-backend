from pydantic import BaseModel


class ModuleBase(BaseModel):
    moduleCode: str
    moduleName: str


class ModuleCreate(ModuleBase):
    pass


class ModuleResponse(ModuleBase):
    moduleID: int

    class Config:
        from_attributes = True