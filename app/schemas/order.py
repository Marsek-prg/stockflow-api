from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.schemas.order_item import OrderItemCreate, OrderItemRead
from app.schemas.pagination import PaginationResponse
from app.schemas.reservation import ReservationRead


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_number: str = Field(min_length=1, max_length=100)
    customer_name: str | None = Field(default=None, max_length=255)
    note: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    customer_name: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    reservations: list[ReservationRead]


class OrderListResponse(PaginationResponse):
    items: list[OrderRead]
