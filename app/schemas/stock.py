from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.stock_movement import MovementType
from app.schemas.pagination import PaginationResponse


class StockItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    created_at: datetime
    updated_at: datetime


class StockItemListResponse(PaginationResponse):
    items: list[StockItemRead]


class StockMovementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int
    warehouse_id: int
    movement_type: MovementType
    quantity: int = Field(ge=0)
    note: str | None = None

    @model_validator(mode="after")
    def validate_quantity_for_movement_type(self) -> Self:
        if self.movement_type in {MovementType.IN, MovementType.OUT}:
            if self.quantity <= 0:
                raise ValueError("IN and OUT movements require quantity greater than 0")
        return self


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    movement_type: MovementType
    quantity: int
    balance_before: int
    balance_after: int
    note: str | None
    created_at: datetime


class StockMovementListResponse(PaginationResponse):
    items: list[StockMovementRead]
