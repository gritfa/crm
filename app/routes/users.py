from fastapi import APIRouter, Form, Request
from sqlalchemy import select

from app.dependencies import AdminUser, DbSession
from app.forms import required
from app.models import User
from app.security import hash_password, validate_csrf
from app.web import flash, redirect, render


router = APIRouter()


@router.get("")
def user_list(request: Request, db: DbSession, user: AdminUser):
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return render(request, "users/list.html", user=user, users=users)


@router.post("")
def create_user(
    request: Request,
    db: DbSession,
    user: AdminUser,
    name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    name = required(name, "姓名")
    phone = required(phone, "手机号")
    if len(password) < 8:
        flash(request, "密码至少需要8位", "danger")
        return redirect("/users")
    if db.scalar(select(User.id).where(User.phone == phone)):
        flash(request, "该手机号已存在", "danger")
        return redirect("/users")
    db.add(
        User(
            name=name,
            phone=phone,
            password_hash=hash_password(password),
            role=role if role in {"admin", "staff"} else "staff",
        )
    )
    db.commit()
    flash(request, "用户创建成功")
    return redirect("/users")


@router.post("/{user_id}/toggle")
def toggle_user(
    user_id: int,
    request: Request,
    db: DbSession,
    user: AdminUser,
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    target = db.get(User, user_id)
    if not target:
        flash(request, "用户不存在", "danger")
    elif target.id == user.id:
        flash(request, "不能停用当前登录账号", "danger")
    else:
        target.is_active = not target.is_active
        db.commit()
        flash(request, "用户状态已更新")
    return redirect("/users")

