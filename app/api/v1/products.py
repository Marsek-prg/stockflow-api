from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.deps import get_db
from app.models.user import User, UserRole
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
)
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])
DbSession = Annotated[Session, Depends(get_db)]
WriteUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: DbSession, _: WriteUser) -> ProductRead:
    return product_service.create_product(db, data)


@router.get("", response_model=ProductListResponse)
def list_products(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: str | None = None,
    is_active: bool | None = None,
) -> ProductListResponse:
    items, total = product_service.list_products(
        db, limit=limit, offset=offset, search=search, is_active=is_active
    )
    return ProductListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession) -> ProductRead:
    return product_service.get_product_by_id(db, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, data: ProductUpdate, db: DbSession, _: WriteUser
) -> ProductRead:
    return product_service.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession, _: WriteUser) -> Response:
    product_service.deactivate_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
