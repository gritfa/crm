from decimal import Decimal
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models import User
from app.security import ensure_csrf_token


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def money(value: Decimal | int | float | None) -> str:
    return f"¥{Decimal(value or 0):,.2f}"


templates.env.filters["money"] = money


def flash(request: Request, message: str, category: str = "success") -> None:
    messages = request.session.setdefault("flashes", [])
    messages.append({"message": message, "category": category})
    request.session["flashes"] = messages


def render(
    request: Request,
    template_name: str,
    *,
    user: User | None = None,
    status_code: int = 200,
    **context,
) -> HTMLResponse:
    payload = {
        "request": request,
        "current_user": user,
        "csrf_token": ensure_csrf_token(request),
        "flashes": request.session.pop("flashes", []),
        **context,
    }
    return templates.TemplateResponse(request, template_name, payload, status_code=status_code)


def redirect(url: str, status_code: int = 303) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status_code)
