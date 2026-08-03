from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Admin


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> Admin:
    admin_id = request.session.get("admin_id")
    admin = db.get(Admin, admin_id) if admin_id else None
    if not admin or not admin.is_active:
        request.session.pop("admin_id", None)
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin
