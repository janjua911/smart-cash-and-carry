import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, PaymentMethod
from app.models.product import Product, StockStatus
from app.models.variant import ProductVariant

class OrderValidationError(ValueError):
    pass

def generate_order_number() -> str:
    date_part = datetime.now().strftime("%y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"SCC-{date_part}-{random_part}"  # ✅ Updated: Smart Cash & Carry prefix

def create_order(
    db: Session,
    cart: dict[str, int],
    customer_name: str,
    phone: str,
    email: str | None,
    address: str,
    notes: str | None,
    payment_method: PaymentMethod,
) -> Order:
    # Parse cart keys
    product_ids: set[int] = set()
    variant_ids: set[int] = set()
    parsed_cart: list[tuple[int, int | None, int]] = []  # product_id, variant_id, qty

    for key, quantity in cart.items():
        parts = key.split(":")
        pid = int(parts[0])
        vid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        product_ids.add(pid)
        if vid:
            variant_ids.add(vid)
        parsed_cart.append((pid, vid, quantity))

    products = db.scalars(
        select(Product).where(Product.id.in_(product_ids)).with_for_update()
    ).all()
    product_map = {p.id: p for p in products}

    variants = db.scalars(
        select(ProductVariant).where(ProductVariant.id.in_(variant_ids)).with_for_update()
    ).all()
    variant_map = {v.id: v for v in variants}

    total = Decimal("0.00")
    prepared_items: list[tuple[Product, ProductVariant | None, int, Decimal]] = []

    for pid, vid, quantity in parsed_cart:
        product = product_map.get(pid)
        if not product or not product.can_order:
            raise OrderValidationError("One of the selected products is no longer available.")

        variant = variant_map.get(vid) if vid else None
        unit_price = product.price
        stock_limit = product.stock_quantity

        if variant:
            if variant.product_id != product.id:
                raise OrderValidationError("Invalid variant selected.")
            if not variant.is_active:
                raise OrderValidationError(f"Variant for {product.name} is no longer available.")
            unit_price = unit_price + Decimal(str(variant.price_adjustment))
            stock_limit = variant.stock_quantity

        if quantity > stock_limit:
            raise OrderValidationError(
                f"Only {stock_limit} unit(s) of {product.name}" +
                (f" ({variant.name})" if variant else "") +
                " are available."
            )

        line_total = unit_price * quantity
        total += line_total
        prepared_items.append((product, variant, quantity, line_total))

    if not prepared_items:
        raise OrderValidationError("Your cart is empty.")

    order = Order(
        order_number=generate_order_number(),
        customer_name=customer_name,
        phone=phone,
        email=email or None,
        address=address,
        notes=notes or None,
        payment_method=payment_method,
        total_amount=total,
    )
    db.add(order)
    db.flush()

    for product, variant, quantity, line_total in prepared_items:
        item_name = product.name
        if variant:
            item_name += f" ({variant.name})"

        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=item_name,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total,
            )
        )

        # Reduce stock
        if variant:
            variant.stock_quantity -= quantity
        else:
            product.stock_quantity -= quantity

        # Update main product status if main stock depleted
        if product.stock_quantity <= 0 and not variant:
            product.stock_status = StockStatus.OUT_OF_STOCK

        # If variant stock depleted, mark variant inactive or just leave it
        if variant and variant.stock_quantity <= 0:
            variant.is_active = False

    db.commit()
    db.refresh(order)
    return order