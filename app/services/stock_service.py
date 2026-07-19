from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock_item import StockItem
from app.models.stock_movement import MovementType, StockMovement
from app.models.warehouse import Warehouse
from app.schemas.stock import StockMovementCreate


def _require_active_product(db: Session, product_id: int) -> None:
    product = db.scalar(
        select(Product.id).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active product not found",
        )


def _require_active_warehouse(db: Session, warehouse_id: int) -> None:
    warehouse = db.scalar(
        select(Warehouse.id).where(
            Warehouse.id == warehouse_id,
            Warehouse.is_active.is_(True),
        )
    )
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active warehouse not found",
        )


def create_stock_movement(db: Session, data: StockMovementCreate) -> StockMovement:
    _require_active_product(db, data.product_id)
    _require_active_warehouse(db, data.warehouse_id)

    stock_item = db.scalar(
        select(StockItem)
        .where(
            StockItem.product_id == data.product_id,
            StockItem.warehouse_id == data.warehouse_id,
        )
        .with_for_update()
    )
    if stock_item is None:
        if data.movement_type == MovementType.OUT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient stock",
            )
        stock_item = StockItem(
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            quantity=0,
        )
        db.add(stock_item)

    balance_before = stock_item.quantity
    if data.movement_type == MovementType.IN:
        balance_after = balance_before + data.quantity
    elif data.movement_type == MovementType.OUT:
        balance_after = balance_before - data.quantity
        if balance_after < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient stock",
            )
    else:
        balance_after = data.quantity

    stock_item.quantity = balance_after
    movement = StockMovement(
        **data.model_dump(),
        balance_before=balance_before,
        balance_after=balance_after,
    )
    db.add(movement)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock movement conflicted with another update",
        ) from exc
    db.refresh(movement)
    return movement


def list_stock_items(
    db: Session,
    limit: int,
    offset: int,
    product_id: int | None = None,
    warehouse_id: int | None = None,
) -> tuple[list[StockItem], int]:
    filters = []
    if product_id is not None:
        filters.append(StockItem.product_id == product_id)
    if warehouse_id is not None:
        filters.append(StockItem.warehouse_id == warehouse_id)

    items_statement = (
        select(StockItem)
        .where(*filters)
        .order_by(StockItem.id)
        .limit(limit)
        .offset(offset)
    )
    count_statement = select(func.count(StockItem.id)).where(*filters)
    return list(db.scalars(items_statement).all()), db.scalar(count_statement) or 0


def list_stock_movements(
    db: Session,
    limit: int,
    offset: int,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    movement_type: MovementType | None = None,
) -> tuple[list[StockMovement], int]:
    filters = []
    if product_id is not None:
        filters.append(StockMovement.product_id == product_id)
    if warehouse_id is not None:
        filters.append(StockMovement.warehouse_id == warehouse_id)
    if movement_type is not None:
        filters.append(StockMovement.movement_type == movement_type)

    items_statement = (
        select(StockMovement)
        .where(*filters)
        .order_by(StockMovement.id)
        .limit(limit)
        .offset(offset)
    )
    count_statement = select(func.count(StockMovement.id)).where(*filters)
    return list(db.scalars(items_statement).all()), db.scalar(count_statement) or 0
