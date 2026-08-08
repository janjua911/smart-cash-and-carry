from decimal import Decimal

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.variant import ProductVariant

def get_cart(request: Request) -> dict[str, int]:
    raw_cart = request.session.get("cart", {})
    cleaned: dict[str, int] = {}
    for key, quantity in raw_cart.items():
        str_key = str(key)
        # Validate key format: "product_id" or "product_id:variant_id"
        parts = str_key.split(":")
        if not parts[0].isdigit():
            continue
        qty = int(quantity)
        if qty > 0:
            cleaned[str_key] = qty
    return cleaned

def save_cart(request: Request, cart: dict[str, int]) -> None:
    request.session["cart"] = cart

def cart_details(db: Session, request: Request) -> tuple[list[dict], Decimal]:
    cart = get_cart(request)
    if not cart:
        return [], Decimal("0.00")

    # Collect product IDs and variant IDs
    product_ids: set[int] = set()
    variant_ids: set[int] = set()
    key_map: dict[str, tuple[int, int | None]] = {}

    for key in cart:
        parts = key.split(":")
        pid = int(parts[0])
        vid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        product_ids.add(pid)
        if vid:
            variant_ids.add(vid)
        key_map[key] = (pid, vid)

    # Load products and variants
    products = db.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.id.in_(product_ids), Product.is_active.is_(True))
    ).unique().all()
    product_map = {p.id: p for p in products}

    variants = db.scalars(
        select(ProductVariant)
        .where(ProductVariant.id.in_(variant_ids), ProductVariant.is_active.is_(True))
    ).all()
    variant_map = {v.id: v for v in variants}

    items: list[dict] = []
    clean_cart: dict[str, int] = {}
    total = Decimal("0.00")

    for key, quantity in cart.items():
        pid, vid = key_map[key]
        product = product_map.get(pid)
        if not product:
            continue

        variant = variant_map.get(vid) if vid else None
        unit_price = product.price
        stock_limit = product.stock_quantity

        if variant:
            unit_price = unit_price + Decimal(str(variant.price_adjustment))
            stock_limit = variant.stock_quantity

        safe_quantity = min(quantity, max(stock_limit, 0))
        if safe_quantity <= 0:
            continue

        line_total = unit_price * safe_quantity
        items.append(
            {
                "product": product,
                "variant": variant,
                "quantity": safe_quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )
        clean_cart[key] = safe_quantity
        total += line_total

    if clean_cart != cart:
        save_cart(request, clean_cart)

    return items, total