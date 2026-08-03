from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import csrf_is_valid, set_flash
from app.database import get_db
from app.models.product import Product
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


@router.post("/add/{product_id}")
def add_to_cart(
    request: Request,
    product_id: int,
    quantity: int = Form(1),
    csrf_token: str = Form(...),
    next_url: str = Form("/cart"),
    db: Session = Depends(get_db),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    product = db.get(Product, product_id)
    if not product or not product.can_order:
        set_flash(request, "This product is currently unavailable.", "error")
        return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)

    cart = get_cart(request)
    current = cart.get(str(product_id), 0)
    cart[str(product_id)] = min(current + max(1, quantity), product.stock_quantity)
    save_cart(request, cart)
    set_flash(request, f"{product.name} added to your cart.")
    return RedirectResponse(safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/update/{product_id}")
def update_cart(
    request: Request,
    product_id: int,
    quantity: int = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    product = db.get(Product, product_id)
    cart = get_cart(request)
    if quantity <= 0 or not product:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = min(quantity, max(product.stock_quantity, 1))
    save_cart(request, cart)
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/remove/{product_id}")
def remove_from_cart(
    request: Request,
    product_id: int,
    csrf_token: str = Form(...),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")
    cart = get_cart(request)
    cart.pop(str(product_id), None)
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
        lines.append(
            f"• {item['product'].name} × {item['quantity']} = Rs. {float(item['line_total']):,.0f}"
        )

    lines.extend([
        "",
        f"Estimated total: Rs. {float(total):,.0f}",
        "Please confirm availability and delivery."
    ])

    url = f"https://wa.me/{branch['whatsapp']}?text={quote(chr(10).join(lines))}"
    
    # ✅ Clear cart after WhatsApp order
    save_cart(request, {})
    
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)