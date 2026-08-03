from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.product import StockStatus


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


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
