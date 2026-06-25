from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.reservation import Reservation, ReservationStatus
from app.models.stock_item import StockItem
from app.models.stock_movement import MovementType, StockMovement
from app.models.warehouse import Warehouse
from app.schemas.order import OrderCreate

StockKey = tuple[int, int]


def _order_options() -> tuple:
    return (
        selectinload(Order.items),
        selectinload(Order.reservations),
    )


def _load_order(db: Session, order_id: int, *, for_update: bool = False) -> Order:
    statement = select(Order).where(Order.id == order_id).options(*_order_options())
    if for_update:
        statement = statement.with_for_update()
    order = db.scalar(statement)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


def _reload_order(db: Session, order_id: int) -> Order:
    statement = (
        select(Order)
        .where(Order.id == order_id)
        .options(*_order_options())
        .execution_options(populate_existing=True)
    )
    order = db.scalar(statement)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


def _require_active_entities(
    db: Session, product_ids: set[int], warehouse_ids: set[int]
) -> None:
    active_products = set(
        db.scalars(
            select(Product.id).where(
                Product.id.in_(product_ids),
                Product.is_active.is_(True),
            )
        ).all()
    )
    if active_products != product_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active product not found",
        )

    active_warehouses = set(
        db.scalars(
            select(Warehouse.id).where(
                Warehouse.id.in_(warehouse_ids),
                Warehouse.is_active.is_(True),
            )
        ).all()
    )
    if active_warehouses != warehouse_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active warehouse not found",
        )


def _stock_keys(items: list[OrderItem]) -> set[StockKey]:
    return {(item.product_id, item.warehouse_id) for item in items}


def _lock_stock_items(db: Session, keys: set[StockKey]) -> dict[StockKey, StockItem]:
    stock_items = db.scalars(
        select(StockItem)
        .where(tuple_(StockItem.product_id, StockItem.warehouse_id).in_(keys))
        .with_for_update()
    ).all()
    return {
        (stock_item.product_id, stock_item.warehouse_id): stock_item
        for stock_item in stock_items
    }


def create_order(db: Session, data: OrderCreate) -> Order:
    product_ids = {item.product_id for item in data.items}
    warehouse_ids = {item.warehouse_id for item in data.items}
    _require_active_entities(db, product_ids, warehouse_ids)

    if db.scalar(select(Order.id).where(Order.order_number == data.order_number)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An order with this order number already exists",
        )

    order = Order(
        order_number=data.order_number,
        customer_name=data.customer_name,
        note=data.note,
        status=OrderStatus.DRAFT,
        items=[OrderItem(**item.model_dump()) for item in data.items],
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An order with this order number already exists",
        ) from exc
    return _reload_order(db, order.id)


def get_order(db: Session, order_id: int) -> Order:
    return _load_order(db, order_id)


def list_orders(
    db: Session,
    limit: int,
    offset: int,
    order_status: OrderStatus | None = None,
) -> tuple[list[Order], int]:
    filters = []
    if order_status is not None:
        filters.append(Order.status == order_status)

    statement = (
        select(Order)
        .where(*filters)
        .options(*_order_options())
        .order_by(Order.id)
        .limit(limit)
        .offset(offset)
    )
    count_statement = select(func.count(Order.id)).where(*filters)
    return list(db.scalars(statement).all()), db.scalar(count_statement) or 0


def reserve_order(db: Session, order_id: int) -> Order:
    order = _load_order(db, order_id, for_update=True)
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only DRAFT orders can be reserved",
        )

    _require_active_entities(
        db,
        {item.product_id for item in order.items},
        {item.warehouse_id for item in order.items},
    )
    keys = _stock_keys(order.items)
    stock_items = _lock_stock_items(db, keys)

    active_rows = db.execute(
        select(
            Reservation.product_id,
            Reservation.warehouse_id,
            func.sum(Reservation.quantity),
        )
        .where(
            tuple_(Reservation.product_id, Reservation.warehouse_id).in_(keys),
            Reservation.status == ReservationStatus.ACTIVE,
        )
        .group_by(Reservation.product_id, Reservation.warehouse_id)
    ).all()
    active_quantities = {
        (product_id, warehouse_id): quantity
        for product_id, warehouse_id, quantity in active_rows
    }
    requested_quantities: dict[StockKey, int] = defaultdict(int)
    for item in order.items:
        requested_quantities[(item.product_id, item.warehouse_id)] += item.quantity

    for key, requested in requested_quantities.items():
        stock_quantity = stock_items[key].quantity if key in stock_items else 0
        available = stock_quantity - active_quantities.get(key, 0)
        if available < requested:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient available stock",
            )

    for item in order.items:
        db.add(
            Reservation(
                order_id=order.id,
                order_item_id=item.id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
                status=ReservationStatus.ACTIVE,
            )
        )
    order.status = OrderStatus.RESERVED
    db.commit()
    return _reload_order(db, order.id)


def confirm_order(db: Session, order_id: int) -> Order:
    order = _load_order(db, order_id, for_update=True)
    if order.status != OrderStatus.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only RESERVED orders can be confirmed",
        )

    reservations = [
        reservation
        for reservation in order.reservations
        if reservation.status == ReservationStatus.ACTIVE
    ]
    keys = {
        (reservation.product_id, reservation.warehouse_id)
        for reservation in reservations
    }
    stock_items = _lock_stock_items(db, keys)
    required_quantities: dict[StockKey, int] = defaultdict(int)
    for reservation in reservations:
        required_quantities[
            (reservation.product_id, reservation.warehouse_id)
        ] += reservation.quantity

    if any(
        key not in stock_items or stock_items[key].quantity < quantity
        for key, quantity in required_quantities.items()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock to confirm order",
        )

    for reservation in reservations:
        key = (reservation.product_id, reservation.warehouse_id)
        stock_item = stock_items[key]
        balance_before = stock_item.quantity
        stock_item.quantity -= reservation.quantity
        db.add(
            StockMovement(
                product_id=reservation.product_id,
                warehouse_id=reservation.warehouse_id,
                movement_type=MovementType.OUT,
                quantity=reservation.quantity,
                balance_before=balance_before,
                balance_after=stock_item.quantity,
                note=f"Order {order.order_number} confirmation",
            )
        )
        reservation.status = ReservationStatus.CONSUMED

    order.status = OrderStatus.CONFIRMED
    db.commit()
    return _reload_order(db, order.id)


def cancel_order(db: Session, order_id: int) -> Order:
    order = _load_order(db, order_id, for_update=True)
    if order.status in {OrderStatus.CONFIRMED, OrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CONFIRMED and CANCELLED orders cannot be changed",
        )

    if order.status == OrderStatus.RESERVED:
        for reservation in order.reservations:
            if reservation.status == ReservationStatus.ACTIVE:
                reservation.status = ReservationStatus.RELEASED

    order.status = OrderStatus.CANCELLED
    db.commit()
    return _reload_order(db, order.id)
