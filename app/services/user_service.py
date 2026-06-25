from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _duplicate_email_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A user with this email already exists",
    )


def create_user(
    db: Session,
    data: UserCreate,
    *,
    role: UserRole = UserRole.VIEWER,
) -> User:
    email = _normalize_email(str(data.email))
    if get_user_by_email(db, email) is not None:
        raise _duplicate_email_error()

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_email_error() from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if (
        user is None
        or not user.is_active
        or not verify_password(password, user.hashed_password)
    ):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def list_users(
    db: Session,
    *,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    items = list(
        db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    )
    total = db.scalar(select(func.count(User.id))) or 0
    return items, total


def update_user(
    db: Session,
    user_id: int,
    data: UserUpdate,
) -> User:
    user = get_user_by_id(db, user_id)
    changes = data.model_dump(exclude_unset=True)

    if "email" in changes:
        email = _normalize_email(str(changes.pop("email")))
        existing = get_user_by_email(db, email)
        if existing is not None and existing.id != user_id:
            raise _duplicate_email_error()
        user.email = email
    if "password" in changes:
        user.hashed_password = hash_password(changes.pop("password"))
    for field, value in changes.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_email_error() from exc
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: int) -> None:
    user = get_user_by_id(db, user_id)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active user not found",
        )
    user.is_active = False
    db.commit()
