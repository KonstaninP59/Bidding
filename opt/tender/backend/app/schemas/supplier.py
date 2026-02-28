from pydantic import BaseModel
from typing import Optional, List
from app.core.enums import SupplierStatus


class SupplierCreate(BaseModel):
    name: str
    email: str
    status: SupplierStatus = SupplierStatus.ACTIVE
    category_ids: Optional[List[int]] = []


class SupplierOut(BaseModel):
    id: int
    name: str
    email: str
    status: SupplierStatus

    model_config = {"from_attributes": True}
