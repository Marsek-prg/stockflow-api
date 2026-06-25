from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.stock_movement import MovementType
from app.schemas.stock import (
    StockItemListResponse,
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementRead,
)
from app.services import stock_service

router = APIRouter(prefix="/stock", tags=["stock"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=StockItemListResponse)
def list_stock_items(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    product_id: int | None = None,
    warehouse_id: int | None = None,
) -> StockItemListResponse:
    items, total = stock_service.list_stock_items(
        db,
        limit=limit,
        offset=offset,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )
    return StockItemListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/movements",
    response_model=StockMovementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    data: StockMovementCreate, db: DbSession
) -> StockMovementRead:
    return stock_service.create_stock_movement(db, data)


@router.get("/movements", response_model=StockMovementListResponse)
def list_stock_movements(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    movement_type: MovementType | None = None,
) -> StockMovementListResponse:
    items, total = stock_service.list_stock_movements(
        db,
        limit=limit,
        offset=offset,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
    )
    return StockMovementListResponse(
        items=items, total=total, limit=limit, offset=offset
    )
