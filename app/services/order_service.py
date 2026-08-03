import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, PaymentMethod
from app.models.product import Product, StockStatus


class OrderValidationError(ValueError):
    pass


def generate_order_number() -> str:
    date_part = datetime.now().strftime("%y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"AIF-{date_part}-{random_part}"


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
    product_ids = [int(product_id) for product_id in cart]
    products = db.scalars(
        select(Product).where(Product.id.in_(product_ids)).with_for_update()
    ).all()
    product_map = {product.id: product for product in products}

    total = Decimal("0.00")
    prepared_items: list[tuple[Product, int, Decimal]] = []
    for product_id, quantity in cart.items():
        product = product_map.get(int(product_id))
        if not product or not product.can_order:
            raise OrderValidationError("One of the selected products is no longer available.")
        if quantity > product.stock_quantity:
            raise OrderValidationError(
                f"Only {product.stock_quantity} unit(s) of {product.name} are available."
            )
        line_total = product.price * quantity
        total += line_total
        prepared_items.append((product, quantity, line_total))

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

    for product, quantity, line_total in prepared_items:
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
                line_total=line_total,
            )
        )
        product.stock_quantity -= quantity
        if product.stock_quantity == 0:
            product.stock_status = StockStatus.OUT_OF_STOCK

    db.commit()
    db.refresh(order)
    return order
