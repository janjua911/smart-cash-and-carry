# app/schemas.py
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.models.product import StockStatus

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str

class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sku: str | None
    price_adjustment: float
    stock_quantity: int
    is_active: bool

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    unit: str
    price: Decimal
    compare_at_price: Decimal | None
    stock_quantity: int
    stock_status: StockStatus
    image_path: str | None
    is_featured: bool
    category: CategoryOut
    variants: list[ProductVariantOut] = []