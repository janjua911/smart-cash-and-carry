from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.security import csrf_is_valid, get_csrf_token, set_flash, verify_password
from app.database import get_db
from app.dependencies import require_admin
from app.models.admin import Admin
from app.models.category import Category
from app.models.order import Order, OrderStatus
from app.models.product import Product, StockStatus
from app.services.slug import unique_category_slug, unique_product_slug
from app.services.storage import delete_local_image, save_product_image
from app.web import template_context, templates


router = APIRouter(prefix="/admin", tags=["admin"])


def verify_csrf(request: Request, form) -> None:
    if not csrf_is_valid(request, form.get("csrf_token")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid form token")


def product_form_values(form) -> dict:
    return {
        "name": str(form.get("name", "")).strip(),
        "slug": str(form.get("slug", "")).strip(),
        "description": str(form.get("description", "")).strip(),
        "unit": str(form.get("unit", "1 item")).strip(),
        "price": str(form.get("price", "")).strip(),
        "compare_at_price": str(form.get("compare_at_price", "")).strip(),
        "stock_quantity": str(form.get("stock_quantity", "0")).strip(),
        "stock_status": str(form.get("stock_status", StockStatus.IN_STOCK.value)),
        "category_id": str(form.get("category_id", "")),
        "is_active": form.get("is_active") == "on",
        "is_featured": form.get("is_featured") == "on",
    }


async def apply_product_form(db: Session, product: Product, form) -> None:
    values = product_form_values(form)
    if len(values["name"]) < 2:
        raise ValueError("Product name must contain at least 2 characters.")
    try:
        category_id = int(values["category_id"])
        stock_quantity = max(0, int(values["stock_quantity"]))
        price = Decimal(values["price"])
        compare_at_price = (
            Decimal(values["compare_at_price"]) if values["compare_at_price"] else None
        )
        stock_status = StockStatus(values["stock_status"])
    except (ValueError, InvalidOperation) as exc:
        raise ValueError("Please provide valid price, stock and category values.") from exc

    if price <= 0:
        raise ValueError("Product price must be greater than zero.")
    if compare_at_price is not None and compare_at_price <= price:
        raise ValueError("Compare-at price must be higher than the selling price.")
    if db.get(Category, category_id) is None:
        raise ValueError("Selected category does not exist.")
    if stock_quantity == 0 and stock_status == StockStatus.IN_STOCK:
        stock_status = StockStatus.OUT_OF_STOCK

    image_upload = form.get("image")
    new_image_path = None
    if getattr(image_upload, "filename", ""):
        new_image_path = await save_product_image(image_upload)

    old_image_path = product.image_path
    product.category_id = category_id
    product.name = values["name"]
    product.slug = unique_product_slug(
        db,
        values["slug"] or values["name"],
        product.id,
    )
    product.description = values["description"]
    product.unit = values["unit"] or "1 item"
    product.price = price
    product.compare_at_price = compare_at_price
    product.stock_quantity = stock_quantity
    product.stock_status = stock_status
    product.is_active = values["is_active"]
    product.is_featured = values["is_featured"]
    if new_image_path:
        product.image_path = new_image_path
        delete_local_image(old_image_path)


@router.get("/login")
def login_page(request: Request):
    if request.session.get("admin_id"):
        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"request": request, "csrf_token": get_csrf_token(request), "error": None},
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    verify_csrf(request, form)
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
    admin = db.scalar(select(Admin).where(Admin.email == email))
    if not admin or not admin.is_active or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "request": request,
                "csrf_token": get_csrf_token(request),
                "error": "Invalid email or password.",
                "email": email,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session.clear()
    request.session["admin_id"] = admin.id
    get_csrf_token(request)
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request):
    form = await request.form()
    verify_csrf(request, form)
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    stats = {
        "products": db.scalar(select(func.count()).select_from(Product)) or 0,
        "active_products": db.scalar(
            select(func.count()).select_from(Product).where(Product.is_active.is_(True))
        )
        or 0,
        "low_stock": db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True), Product.stock_quantity <= 5)
        )
        or 0,
        "orders": db.scalar(select(func.count()).select_from(Order)) or 0,
        "pending_orders": db.scalar(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
        )
        or 0,
        "revenue": db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.status != OrderStatus.CANCELLED
            )
        )
        or 0,
    }
    recent_orders = db.scalars(
        select(Order).order_by(Order.created_at.desc()).limit(8)
    ).all()
    low_stock_products = db.scalars(
        select(Product)
        .where(Product.is_active.is_(True), Product.stock_quantity <= 5)
        .order_by(Product.stock_quantity)
        .limit(8)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context=template_context(
            request,
            admin=admin,
            stats=stats,
            recent_orders=recent_orders,
            low_stock_products=low_stock_products,
        ),
    )


@router.get("/products")
def products_list(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    products = db.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .order_by(Product.created_at.desc())
    ).unique().all()
    return templates.TemplateResponse(
        request=request,
        name="admin/products/list.html",
        context=template_context(request, admin=admin, products=products),
    )


@router.get("/products/new")
def product_new_page(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    categories = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/products/form.html",
        context=template_context(
            request, admin=admin, product=None, categories=categories, form_values={}, error=None
        ),
    )


@router.post("/products/new")
async def product_create(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, form)
    product = Product()
    try:
        await apply_product_form(db, product, form)
        db.add(product)
        db.commit()
    except ValueError as exc:
        db.rollback()
        categories = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
        return templates.TemplateResponse(
            request=request,
            name="admin/products/form.html",
            context=template_context(
                request,
                admin=admin,
                product=None,
                categories=categories,
                form_values=product_form_values(form),
                error=str(exc),
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    set_flash(request, "Product created successfully.")
    return RedirectResponse("/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/products/{product_id}/edit")
def product_edit_page(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    categories = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/products/form.html",
        context=template_context(
            request, admin=admin, product=product, categories=categories, form_values={}, error=None
        ),
    )


@router.post("/products/{product_id}/edit")
async def product_update(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    form = await request.form()
    verify_csrf(request, form)
    try:
        await apply_product_form(db, product, form)
        db.commit()
    except ValueError as exc:
        db.rollback()
        categories = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
        return templates.TemplateResponse(
            request=request,
            name="admin/products/form.html",
            context=template_context(
                request,
                admin=admin,
                product=product,
                categories=categories,
                form_values=product_form_values(form),
                error=str(exc),
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    set_flash(request, "Product updated successfully.")
    return RedirectResponse("/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/products/{product_id}/archive")
async def product_archive(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, form)
    product = db.get(Product, product_id)
    if product:
        product.is_active = False
        db.commit()
        set_flash(request, "Product archived. Existing order history remains safe.")
    return RedirectResponse("/admin/products", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories")
def categories_page(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    categories = db.scalars(select(Category).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/categories/list.html",
        context=template_context(request, admin=admin, categories=categories),
    )


@router.post("/categories")
async def category_create(
    request: Request,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, form)
    name = str(form.get("name", "")).strip()
    if len(name) < 2:
        set_flash(request, "Category name is too short.", "error")
    elif db.scalar(select(Category).where(func.lower(Category.name) == name.lower())):
        set_flash(request, "This category already exists.", "error")
    else:
        db.add(Category(name=name, slug=unique_category_slug(db, name)))
        db.commit()
        set_flash(request, "Category created successfully.")
    return RedirectResponse("/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/toggle")
async def category_toggle(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, form)
    category = db.get(Category, category_id)
    if category:
        category.is_active = not category.is_active
        db.commit()
    return RedirectResponse("/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/orders")
def orders_list(
    request: Request,
    order_status: str = "",
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    query = select(Order).order_by(Order.created_at.desc())
    if order_status:
        try:
            query = query.where(Order.status == OrderStatus(order_status))
        except ValueError:
            order_status = ""
    orders = db.scalars(query).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/orders/list.html",
        context=template_context(
            request,
            admin=admin,
            orders=orders,
            statuses=list(OrderStatus),
            selected_status=order_status,
        ),
    )


@router.get("/orders/{order_id}")
def order_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
):
    order = db.scalar(
        select(Order).options(joinedload(Order.items)).where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/orders/detail.html",
        context=template_context(
            request, admin=admin, order=order, statuses=list(OrderStatus)
        ),
    )


@router.post("/orders/{order_id}/status")
async def order_status_update(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, form)
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        order.status = OrderStatus(str(form.get("status", "")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status") from exc
    db.commit()
    set_flash(request, "Order status updated.")
    return RedirectResponse(
        f"/admin/orders/{order.id}", status_code=status.HTTP_303_SEE_OTHER
    )
