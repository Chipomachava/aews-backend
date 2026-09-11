from pydantic import BaseModel


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str