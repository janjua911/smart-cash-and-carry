from decimal import Decimal

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.core.config import settings
from app.core.config import BRANCHES  # ✅ Step 2: Branch import add kiya
from app.core.security import get_csrf_token, pop_flash


templates = Jinja2Templates(directory=str(settings.templates_dir))


def format_currency(value: Decimal | float | int | None) -> str:
    if value is None:
        return "Rs. 0"
    return f"Rs. {float(value):,.0f}"


templates.env.filters["currency"] = format_currency
templates.env.globals["settings"] = settings


# ✅ Step 2: Branch helper function add kiya
def get_branch(request: Request):
    branch_id = request.session.get("branch_id", "zafarwal")
    for branch in BRANCHES:
        if branch["id"] == branch_id:
            return branch
    return BRANCHES[0]


# ✅ Step 2: template_context function update kiya - branches & selected_branch add kiye
def template_context(request: Request, **kwargs) -> dict:
    return {
        "request": request,
        "csrf_token": get_csrf_token(request),
        "flash": pop_flash(request),
        "cart_count": sum(request.session.get("cart", {}).values()),
        "branches": BRANCHES,
        "selected_branch": get_branch(request),
        **kwargs,
    }