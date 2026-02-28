from pydantic import BaseModel
from typing import List, Optional
from app.core.enums import RequestStatus


class RequestItemBase(BaseModel):
    name: str
    description: Optional[str]
    quantity: float
    unit: str


class RequestItemCreate(RequestItemBase):
    pass


class RequestItemOut(RequestItemBase):
    id: int

    model_config = {"from_attributes": True}


class RequestBase(BaseModel):
    subject: str
    description: Optional[str]
    category_id: int


class RequestCreate(RequestBase):
    items: List[RequestItemCreate]


class RequestUpdate(BaseModel):
    subject: Optional[str]
    description: Optional[str]
    status: Optional[RequestStatus]


class RequestOut(RequestBase):
    id: int
    status: RequestStatus
    items: List[RequestItemOut]

    model_config = {"from_attributes": True}
