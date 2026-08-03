import hmac
import secrets

from pwdlib import PasswordHash
from starlette.requests import Request


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


def get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def csrf_is_valid(request: Request, submitted_token: str | None) -> bool:
    saved_token = request.session.get("csrf_token")
    return bool(
        saved_token
        and submitted_token
        and hmac.compare_digest(saved_token, submitted_token)
    )


def set_flash(request: Request, message: str, category: str = "success") -> None:
    request.session["flash"] = {"message": message, "category": category}


def pop_flash(request: Request) -> dict[str, str] | None:
    return request.session.pop("flash", None)
