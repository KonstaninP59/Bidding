from pydantic import BaseModel
from typing import Optional


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str]


class CategoryOut(CategoryCreate):
    id: int

    model_config = {"from_attributes": True}
