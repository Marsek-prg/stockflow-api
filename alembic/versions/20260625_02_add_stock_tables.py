"""add stock items and stock movements

Revision ID: 20260625_02
Revises: 20260625_01
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260625_02"
down_revision: str | None = "20260625_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity >= 0", name="ck_stock_items_quantity_non_negative"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_stock_items_product_warehouse",
        ),
    )
    op.create_index(
        "ix_stock_items_product_id", "stock_items", ["product_id"], unique=False
    )
    op.create_index(
        "ix_stock_items_warehouse_id", "stock_items", ["warehouse_id"], unique=False
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("balance_before", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type IN ('IN', 'OUT', 'ADJUSTMENT')",
            name="ck_stock_movements_movement_type",
        ),
        sa.CheckConstraint(
            "quantity >= 0", name="ck_stock_movements_quantity_non_negative"
        ),
        sa.CheckConstraint(
            "balance_before >= 0",
            name="ck_stock_movements_balance_before_non_negative",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_stock_movements_balance_after_non_negative",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_movements_created_at",
        "stock_movements",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_movement_type",
        "stock_movements",
        ["movement_type"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_product_id",
        "stock_movements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_warehouse_id",
        "stock_movements",
        ["warehouse_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_warehouse_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_product_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_movement_type", table_name="stock_movements")
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_stock_items_warehouse_id", table_name="stock_items")
    op.drop_index("ix_stock_items_product_id", table_name="stock_items")
    op.drop_table("stock_items")
