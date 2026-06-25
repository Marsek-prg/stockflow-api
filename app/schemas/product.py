from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.pagination import PaginationResponse


class ProductBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    unit: str = Field(default="pcs", min_length=1, max_length=50)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        required_fields = {"sku", "name", "unit", "is_active"}
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in required_fields
        ):
            raise ValueError("Required product fields cannot be null")
        return self


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProductListResponse(PaginationResponse):
    items: list[ProductRead]
