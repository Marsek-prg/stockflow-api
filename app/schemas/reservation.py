from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus
from app.schemas.pagination import PaginationResponse


class ReservationCreate(BaseModel):
    order_id: int
    order_item_id: int
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    order_item_id: int
    product_id: int
    warehouse_id: int
    quantity: int
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime


class ReservationListResponse(PaginationResponse):
    items: list[ReservationRead]
