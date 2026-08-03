import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def unique_product_slug(db: Session, value: str, product_id: int | None = None) -> str:
    base = slugify(value)
    candidate = base
    counter = 2
    while True:
        query = select(Product.id).where(Product.slug == candidate)
        if product_id:
            query = query.where(Product.id != product_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


def unique_category_slug(db: Session, value: str) -> str:
    base = slugify(value)
    candidate = base
    counter = 2
    while db.scalar(select(Category.id).where(Category.slug == candidate)) is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate
