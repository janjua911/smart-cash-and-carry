from sqlalchemy import ForeignKey, Numeric, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))  # e.g., "1L", "Red", "500g"
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    price_adjustment: Mapped[float] = mapped_column(default=0.0)  # +50 or -20 from base price
    stock_quantity: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    product: Mapped["Product"] = relationship(back_populates="variants")