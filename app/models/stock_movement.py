from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MovementType(StrEnum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0", name="ck_stock_movements_quantity_non_negative"
        ),
        CheckConstraint(
            "balance_before >= 0",
            name="ck_stock_movements_balance_before_non_negative",
        ),
        CheckConstraint(
            "balance_after >= 0",
            name="ck_stock_movements_balance_after_non_negative",
        ),
        Index("ix_stock_movements_product_id", "product_id"),
        Index("ix_stock_movements_warehouse_id", "warehouse_id"),
        Index("ix_stock_movements_movement_type", "movement_type"),
        Index("ix_stock_movements_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False, length=20)
    )
    quantity: Mapped[int]
    balance_before: Mapped[int]
    balance_after: Mapped[int]
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
