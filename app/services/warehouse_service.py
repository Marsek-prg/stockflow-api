from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


def check_code_uniqueness(
    db: Session, code: str, exclude_warehouse_id: int | None = None
) -> None:
    statement = select(Warehouse.id).where(Warehouse.code == code)
    if exclude_warehouse_id is not None:
        statement = statement.where(Warehouse.id != exclude_warehouse_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with this code already exists",
        )


def create_warehouse(db: Session, data: WarehouseCreate) -> Warehouse:
    check_code_uniqueness(db, data.code)
    warehouse = Warehouse(**data.model_dump())
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with this code already exists",
        ) from exc
    db.refresh(warehouse)
    return warehouse


def get_warehouse_by_id(db: Session, warehouse_id: int) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found"
        )
    return warehouse


def list_warehouses(
    db: Session,
    limit: int,
    offset: int,
    search: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Warehouse], int]:
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(Warehouse.code.ilike(pattern), Warehouse.name.ilike(pattern))
        )
    if is_active is not None:
        filters.append(Warehouse.is_active == is_active)

    items_statement = (
        select(Warehouse)
        .where(*filters)
        .order_by(Warehouse.id)
        .limit(limit)
        .offset(offset)
    )
    count_statement = select(func.count(Warehouse.id)).where(*filters)
    return list(db.scalars(items_statement).all()), db.scalar(count_statement) or 0


def update_warehouse(
    db: Session, warehouse_id: int, data: WarehouseUpdate
) -> Warehouse:
    warehouse = get_warehouse_by_id(db, warehouse_id)
    changes = data.model_dump(exclude_unset=True)
    if "code" in changes:
        check_code_uniqueness(db, changes["code"], exclude_warehouse_id=warehouse_id)
    for field, value in changes.items():
        setattr(warehouse, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with this code already exists",
        ) from exc
    db.refresh(warehouse)
    return warehouse


def deactivate_warehouse(db: Session, warehouse_id: int) -> None:
    warehouse = get_warehouse_by_id(db, warehouse_id)
    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active warehouse not found"
        )
    warehouse.is_active = False
    db.commit()
