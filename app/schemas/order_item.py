from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginationResponse


class OrderItemCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    warehouse_id: int
    quantity: int
    created_at: datetime


class OrderItemListResponse(PaginationResponse):
    items: list[OrderItemRead]
