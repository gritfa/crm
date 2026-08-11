from fastapi import APIRouter, Form, Request
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import load_user, validate_csrf, verify_password
from app.web import flash, redirect, render


router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    with SessionLocal() as db:
        if load_user(request, db):
            return redirect("/")
    return render(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == phone.strip()))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            return render(
                request,
                "login.html",
                status_code=400,
                error="手机号或密码错误",
                phone=phone,
            )
        request.session.clear()
        request.session["user_id"] = user.id
        flash(request, f"欢迎回来，{user.name}")
        return redirect("/")


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return redirect("/login")
