from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.deps import get_db
from app.models.user import UserRole
from app.schemas.user import UserListResponse, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=UserListResponse)
def list_users(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    items, total = user_service.list_users(db, limit=limit, offset=offset)
    return UserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession) -> UserRead:
    return user_service.get_user_by_id(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: DbSession) -> UserRead:
    return user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DbSession) -> Response:
    user_service.deactivate_user(db, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
