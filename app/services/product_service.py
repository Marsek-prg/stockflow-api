from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def check_sku_uniqueness(
    db: Session, sku: str, exclude_product_id: int | None = None
) -> None:
    statement = select(Product.id).where(Product.sku == sku)
    if exclude_product_id is not None:
        statement = statement.where(Product.id != exclude_product_id)
    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        )


def create_product(db: Session, data: ProductCreate) -> Product:
    check_sku_uniqueness(db, data.sku)
    product = Product(**data.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        ) from exc
    db.refresh(product)
    return product


def get_product_by_id(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


def list_products(
    db: Session,
    limit: int,
    offset: int,
    search: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Product], int]:
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(or_(Product.sku.ilike(pattern), Product.name.ilike(pattern)))
    if is_active is not None:
        filters.append(Product.is_active == is_active)

    items_statement = (
        select(Product).where(*filters).order_by(Product.id).limit(limit).offset(offset)
    )
    count_statement = select(func.count(Product.id)).where(*filters)
    return list(db.scalars(items_statement).all()), db.scalar(count_statement) or 0


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product_by_id(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    if "sku" in changes:
        check_sku_uniqueness(db, changes["sku"], exclude_product_id=product_id)
    for field, value in changes.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        ) from exc
    db.refresh(product)
    return product


def deactivate_product(db: Session, product_id: int) -> None:
    product = get_product_by_id(db, product_id)
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active product not found"
        )
    product.is_active = False
    db.commit()
