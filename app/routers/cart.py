from urllib.parse import quote
from decimal import Decimal  # ✅ Added for variant price calculation

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import csrf_is_valid, set_flash
from app.database import get_db
from app.models.product import Product
from app.models.variant import ProductVariant  # ✅ Added variant model import
from app.services.cart_service import cart_details, get_cart, save_cart
from app.web import template_context, templates, get_branch


router = APIRouter(prefix="/cart", tags=["cart"])


def safe_next_url(value: str | None, fallback: str = "/cart") -> str:
    return value if value and value.startswith("/") and not value.startswith("//") else fallback


@router.get("")
def view_cart(request: Request, db: Session = Depends(get_db)):
    items, total = cart_details(db, request)
    return templates.TemplateResponse(
        request=request,
        name="store/cart.html",
        context=template_context(request, items=items, total=total),
    )


# ✅ Updated: Cart add with variant support
@router.post("/add")
def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(1),
    variant_id: int | None = Form(None),
    csrf_token: str = Form(...),
    next_url: str = Form("/cart"),
    db: Session = Depends(get_db),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    
    # Get product
    product = db.get(Product, product_id)
    if not product or not product.can_order:
        set_flash(request, "This product is currently unavailable.", "error")
        return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)
    
    # ✅ Variant validation
    cart = get_cart(request)
    cart_key = str(product_id)  # Default: no variant
    
    if variant_id:
        variant = db.get(ProductVariant, variant_id)
        if not variant or variant.product_id != product.id or not variant.is_active:
            set_flash(request, "Selected variant is not available.", "error")
            return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)
        
        # Check variant stock
        cart_key = f"{product_id}:{variant_id}"
        current_qty = cart.get(cart_key, 0)
        if current_qty + max(1, quantity) > variant.stock_quantity:
            set_flash(request, f"Only {variant.stock_quantity} units available for this variant.", "error")
            return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)
    else:
        # No variant - check main product stock
        current_qty = cart.get(cart_key, 0)
        if current_qty + max(1, quantity) > product.stock_quantity:
            set_flash(request, f"Only {product.stock_quantity} units available.", "error")
            return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)
    
    # ✅ Add to cart with variant key
    cart[cart_key] = cart.get(cart_key, 0) + max(1, quantity)
    save_cart(request, cart)
    
    if variant_id:
        set_flash(request, f"{product.name} ({variant.name}) added to your cart.")
    else:
        set_flash(request, f"{product.name} added to your cart.")
    
    return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)


# ✅ Updated: Update cart with variant support
@router.post("/update/{cart_key}")
def update_cart(
    request: Request,
    cart_key: str,
    quantity: int = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    
    cart = get_cart(request)
    
    # Parse cart key to get product_id and variant_id
    parts = cart_key.split(":")
    product_id = int(parts[0]) if parts else 0
    variant_id = int(parts[1]) if len(parts) > 1 else None
    
    if quantity <= 0:
        cart.pop(cart_key, None)
    else:
        # Check stock limits
        product = db.get(Product, product_id)
        if product:
            if variant_id:
                variant = db.get(ProductVariant, variant_id)
                if variant and variant.is_active:
                    cart[cart_key] = min(quantity, variant.stock_quantity)
                else:
                    cart.pop(cart_key, None)
            else:
                cart[cart_key] = min(quantity, product.stock_quantity)
    
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)


# ✅ Updated: Remove from cart with variant support
@router.post("/remove/{cart_key}")
def remove_from_cart(
    request: Request,
    cart_key: str,
    csrf_token: str = Form(...),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    
    cart = get_cart(request)
    cart.pop(cart_key, None)
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/whatsapp")
def whatsapp_order(request: Request, db: Session = Depends(get_db)):
    items, total = cart_details(db, request)
    if not items:
        set_flash(request, "Add products before creating a WhatsApp order.", "error")
        return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)

    branch = get_branch(request)

    lines = ["Assalam-o-Alaikum, I want to place a SMART CASH AND CARRY order:", ""]
    lines.append(f"📍 Branch: {branch['name']}")
    lines.append("")

    for item in items:
        # ✅ Show variant name if present
        product_name = item['product'].name
        if item.get('variant'):
            product_name += f" ({item['variant'].name})"
        
        lines.append(
            f"• {product_name} × {item['quantity']} = Rs. {float(item['line_total']):,.0f}"
        )

    lines.extend([
        "",
        f"Estimated total: Rs. {float(total):,.0f}",
        "Please confirm availability and delivery."
    ])

    url = f"https://wa.me/{branch['whatsapp']}?text={quote(chr(10).join(lines))}"
    
    # Clear cart after WhatsApp order
    save_cart(request, {})
    
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)
