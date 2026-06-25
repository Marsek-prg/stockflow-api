from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.deps import get_db
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderListResponse, OrderRead
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])
DbSession = Annotated[Session, Depends(get_db)]
WriteUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: DbSession, _: WriteUser) -> OrderRead:
    return order_service.create_order(db, data)


@router.get("", response_model=OrderListResponse)
def list_orders(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order_status: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> OrderListResponse:
    items, total = order_service.list_orders(
        db,
        limit=limit,
        offset=offset,
        order_status=order_status,
    )
    return OrderListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: DbSession) -> OrderRead:
    return order_service.get_order(db, order_id)


@router.post("/{order_id}/reserve", response_model=OrderRead)
def reserve_order(order_id: int, db: DbSession, _: WriteUser) -> OrderRead:
    return order_service.reserve_order(db, order_id)


@router.post("/{order_id}/confirm", response_model=OrderRead)
def confirm_order(order_id: int, db: DbSession, _: WriteUser) -> OrderRead:
    return order_service.confirm_order(db, order_id)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(order_id: int, db: DbSession, _: WriteUser) -> OrderRead:
    return order_service.cancel_order(db, order_id)
