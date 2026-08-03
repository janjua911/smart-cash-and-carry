from decimal import Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product


def get_cart(request: Request) -> dict[str, int]:
    raw_cart = request.session.get("cart", {})
    return {
        str(product_id): max(1, int(quantity))
        for product_id, quantity in raw_cart.items()
        if str(product_id).isdigit() and int(quantity) > 0
    }


def save_cart(request: Request, cart: dict[str, int]) -> None:
    request.session["cart"] = cart


def cart_details(db: Session, request: Request) -> tuple[list[dict], Decimal]:
    cart = get_cart(request)
    if not cart:
        return [], Decimal("0.00")

    ids = [int(product_id) for product_id in cart]
    products = db.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.id.in_(ids), Product.is_active.is_(True))
    ).all()
    product_map = {product.id: product for product in products}

    items: list[dict] = []
    clean_cart: dict[str, int] = {}
    total = Decimal("0.00")
    for product_id, quantity in cart.items():
        product = product_map.get(int(product_id))
        if not product:
            continue
        safe_quantity = min(quantity, max(product.stock_quantity, 1))
        line_total = product.price * safe_quantity
        items.append(
            {
                "product": product,
                "quantity": safe_quantity,
                "line_total": line_total,
            }
        )
        clean_cart[product_id] = safe_quantity
        total += line_total

    if clean_cart != cart:
        save_cart(request, clean_cart)
    return items, total
