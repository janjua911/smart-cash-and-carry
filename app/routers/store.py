from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse  # ✅ Step 3: RedirectResponse import
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.category import Category
from app.models.product import Product
from app.web import template_context, templates
from app.core.config import BRANCHES  # ✅ Step 3: BRANCHES import


router = APIRouter()


@router.get("/")
def home(
    request: Request,
    q: str = "",
    category: str = "",
    db: Session = Depends(get_db),
):
    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.is_active.is_(True))
        .order_by(Product.is_featured.desc(), Product.created_at.desc())
    )
    if q.strip():
        search_term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )
    if category:
        query = query.join(Product.category).where(Category.slug == category)

    products = db.scalars(query).unique().all()
    categories = db.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="store/index.html",
        context=template_context(
            request,
            products=products,
            categories=categories,
            selected_category=category,
            search_query=q,
        ),
    )


@router.get("/products/{slug}")
def product_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    product = db.scalar(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.slug == slug, Product.is_active.is_(True))
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return templates.TemplateResponse(
        request=request,
        name="store/product_detail.html",
        context=template_context(request, product=product),
    )


# ✅ Naya route - Dedicated Category Pages
@router.get("/category/{slug}")
def category_page(request: Request, slug: str, db: Session = Depends(get_db)):
    category = db.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    products = db.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.is_active.is_(True), Product.category_id == category.id)
        .order_by(Product.is_featured.desc(), Product.created_at.desc())
    ).unique().all()
    
    categories = db.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    ).all()
    
    return templates.TemplateResponse(
        request=request,
        name="store/category.html",
        context=template_context(
            request,
            products=products,
            categories=categories,
            current_category=category,
        ),
    )


# ✅ Step 3: Branch selection route (last route)
@router.post("/set-branch")
async def set_branch(request: Request):
    form = await request.form()
    branch_id = str(form.get("branch_id", "zafarwal"))
    valid_ids = {b["id"] for b in BRANCHES}
    if branch_id in valid_ids:
        request.session["branch_id"] = branch_id
    next_url = str(form.get("next", "/"))
    if not next_url.startswith("/"):
        next_url = "/"
    return RedirectResponse(next_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/debug-branch")
def debug_branch(request: Request):
    from app.web import get_branch
    branch = get_branch(request)
    return {
        "session_branch_id": request.session.get("branch_id"),
        "resolved_branch": branch,
        "all_branches": [b["id"] for b in BRANCHES],
    }
