from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import csrf_is_valid, set_flash
from app.database import get_db
from app.models.order import PaymentMethod
from app.services.cart_service import cart_details, get_cart, save_cart
from app.services.order_service import OrderValidationError, create_order
from app.web import template_context, templates


router = APIRouter(tags=["checkout"])


@router.get("/checkout")
def checkout_page(request: Request, db: Session = Depends(get_db)):
    items, total = cart_details(db, request)
    if not items:
        set_flash(request, "Your cart is empty.", "error")
        return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="store/checkout.html",
        context=template_context(request, items=items, total=total, form_data={}),
    )


@router.post("/checkout")
def place_order(
    request: Request,
    customer_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    address: str = Form(...),
    notes: str = Form(""),
    payment_method: PaymentMethod = Form(PaymentMethod.CASH_ON_DELIVERY),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    if not csrf_is_valid(request, csrf_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")

    form_data = {
        "customer_name": customer_name.strip(),
        "phone": phone.strip(),
        "email": email.strip(),
        "address": address.strip(),
        "notes": notes.strip(),
        "payment_method": payment_method.value,
    }
    items, total = cart_details(db, request)
    error = None
    if len(form_data["customer_name"]) < 2:
        error = "Please enter your full name."
    elif len(form_data["phone"]) < 10:
        error = "Please enter a valid phone number."
    elif len(form_data["address"]) < 10:
        error = "Please enter a complete delivery address."
    elif not items:
        error = "Your cart is empty."

    if error:
        return templates.TemplateResponse(
            request=request,
            name="store/checkout.html",
            context=template_context(request, items=items, total=total, form_data=form_data, error=error),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        order = create_order(
            db=db,
            cart=get_cart(request),
            customer_name=form_data["customer_name"],
            phone=form_data["phone"],
            email=form_data["email"] or None,
            address=form_data["address"],
            notes=form_data["notes"] or None,
            payment_method=payment_method,
        )
    except OrderValidationError as exc:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="store/checkout.html",
            context=template_context(
                request, items=items, total=total, form_data=form_data, error=str(exc)
            ),
            status_code=status.HTTP_409_CONFLICT,
        )

    save_cart(request, {})
    request.session["last_order_number"] = order.order_number
    return RedirectResponse(
        f"/order-success/{order.order_number}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/order-success/{order_number}")
def order_success(request: Request, order_number: str):
    if request.session.get("last_order_number") != order_number:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return templates.TemplateResponse(
        request=request,
        name="store/order_success.html",
        context=template_context(request, order_number=order_number),
    )
