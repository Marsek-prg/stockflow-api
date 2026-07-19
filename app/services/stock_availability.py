from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus

type StockKey = tuple[int, int]


def get_active_reserved_quantities(
    db: Session, keys: set[StockKey]
) -> dict[StockKey, int]:
    """Return active reservation totals for each requested stock key."""
    if not keys:
        return {}

    rows = db.execute(
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
    return {
        (product_id, warehouse_id): int(quantity)
        for product_id, warehouse_id, quantity in rows
    }


def calculate_available_quantity(
    physical_quantity: int, active_reserved_quantity: int
) -> int:
    return physical_quantity - active_reserved_quantity
