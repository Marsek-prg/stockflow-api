"""Pydantic schemas package."""

from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.order import OrderCreate, OrderListResponse, OrderRead
from app.schemas.order_item import (
    OrderItemCreate,
    OrderItemListResponse,
    OrderItemRead,
)
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from app.schemas.reservation import (
    ReservationCreate,
    ReservationListResponse,
    ReservationRead,
)
from app.schemas.stock import (
    StockItemListResponse,
    StockItemRead,
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementRead,
)
from app.schemas.user import UserCreate, UserListResponse, UserRead, UserUpdate
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseUpdate,
)

__all__ = [
    "LoginRequest",
    "OrderCreate",
    "OrderItemCreate",
    "OrderItemListResponse",
    "OrderItemRead",
    "OrderListResponse",
    "OrderRead",
    "ProductCreate",
    "ProductListResponse",
    "ProductRead",
    "ProductUpdate",
    "ReservationCreate",
    "ReservationListResponse",
    "ReservationRead",
    "StockItemListResponse",
    "StockItemRead",
    "StockMovementCreate",
    "StockMovementListResponse",
    "StockMovementRead",
    "TokenResponse",
    "UserCreate",
    "UserListResponse",
    "UserRead",
    "UserUpdate",
    "WarehouseCreate",
    "WarehouseListResponse",
    "WarehouseRead",
    "WarehouseUpdate",
]
