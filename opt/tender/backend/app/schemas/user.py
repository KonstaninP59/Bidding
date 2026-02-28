from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role_id: int


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role_id: int

    model_config = {"from_attributes": True}
