from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseUpdate,
)
from app.services import warehouse_service

router = APIRouter(prefix="/warehouses", tags=["warehouses"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def create_warehouse(data: WarehouseCreate, db: DbSession) -> WarehouseRead:
    return warehouse_service.create_warehouse(db, data)


@router.get("", response_model=WarehouseListResponse)
def list_warehouses(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: str | None = None,
    is_active: bool | None = None,
) -> WarehouseListResponse:
    items, total = warehouse_service.list_warehouses(
        db, limit=limit, offset=offset, search=search, is_active=is_active
    )
    return WarehouseListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(warehouse_id: int, db: DbSession) -> WarehouseRead:
    return warehouse_service.get_warehouse_by_id(db, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: int, data: WarehouseUpdate, db: DbSession
) -> WarehouseRead:
    return warehouse_service.update_warehouse(db, warehouse_id, data)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(warehouse_id: int, db: DbSession) -> Response:
    warehouse_service.deactivate_warehouse(db, warehouse_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
