import uuid

from pydantic import BaseModel

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str
    turnstile_token: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    full_name: str

    model_config = {"from_attributes": True}
