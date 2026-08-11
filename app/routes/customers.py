from fastapi import APIRouter, Form, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from app.forms import optional, required
from app.models import Contact, Customer
from app.security import validate_csrf
from app.web import flash, redirect, render


router = APIRouter()


@router.get("")
def customer_list(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = "",
    status: str = "active",
):
    stmt = select(Customer).options(selectinload(Customer.owner)).order_by(Customer.updated_at.desc())
    if q.strip():
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(keyword), Customer.phone.ilike(keyword)))
    if status in {"active", "inactive"}:
        stmt = stmt.where(Customer.status == status)
    customers = db.scalars(stmt).all()
    return render(
        request,
        "customers/list.html",
        user=user,
        customers=customers,
        q=q,
        status=status,
    )


@router.get("/new")
def customer_new(request: Request, user: CurrentUser):
    return render(request, "customers/form.html", user=user, customer=None)


@router.post("")
def customer_create(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(...),
    contact_name: str = Form(""),
    phone: str = Form(""),
    source: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    name = required(name, "客户名称")
    if db.scalar(select(Customer.id).where(Customer.name == name)):
        flash(request, "客户名称已存在", "danger")
        return redirect("/customers/new")
    customer = Customer(
        name=name,
        contact_name=optional(contact_name),
        phone=optional(phone),
        source=optional(source),
        notes=optional(notes),
        owner_id=user.id,
    )
    db.add(customer)
    db.commit()
    flash(request, "客户创建成功")
    return redirect(f"/customers/{customer.id}")


@router.get("/{customer_id}")
def customer_detail(customer_id: int, request: Request, db: DbSession, user: CurrentUser):
    customer = db.scalar(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(
            selectinload(Customer.contacts),
            selectinload(Customer.contracts),
            selectinload(Customer.owner),
        )
    )
    if not customer:
        flash(request, "客户不存在", "danger")
        return redirect("/customers")
    return render(request, "customers/detail.html", user=user, customer=customer)


@router.get("/{customer_id}/edit")
def customer_edit(customer_id: int, request: Request, db: DbSession, user: CurrentUser):
    customer = db.get(Customer, customer_id)
    if not customer:
        flash(request, "客户不存在", "danger")
        return redirect("/customers")
    return render(request, "customers/form.html", user=user, customer=customer)


@router.post("/{customer_id}")
def customer_update(
    customer_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(...),
    contact_name: str = Form(""),
    phone: str = Form(""),
    source: str = Form(""),
    status: str = Form("active"),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    customer = db.get(Customer, customer_id)
    if not customer:
        flash(request, "客户不存在", "danger")
        return redirect("/customers")
    cleaned_name = required(name, "客户名称")
    duplicate = db.scalar(
        select(Customer.id).where(Customer.name == cleaned_name, Customer.id != customer_id)
    )
    if duplicate:
        flash(request, "客户名称已存在", "danger")
        return redirect(f"/customers/{customer_id}/edit")
    customer.name = cleaned_name
    customer.contact_name = optional(contact_name)
    customer.phone = optional(phone)
    customer.source = optional(source)
    customer.status = status if status in {"active", "inactive"} else "active"
    customer.notes = optional(notes)
    db.commit()
    flash(request, "客户资料已更新")
    return redirect(f"/customers/{customer_id}")


@router.post("/{customer_id}/contacts")
def contact_create(
    customer_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(...),
    phone: str = Form(""),
    position: str = Form(""),
    is_primary: str | None = Form(None),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    customer = db.get(Customer, customer_id)
    if not customer:
        flash(request, "客户不存在", "danger")
        return redirect("/customers")
    make_primary = is_primary == "on"
    if make_primary:
        for contact in db.scalars(select(Contact).where(Contact.customer_id == customer_id)):
            contact.is_primary = False
    db.add(
        Contact(
            customer_id=customer_id,
            name=required(name, "联系人姓名"),
            phone=optional(phone),
            position=optional(position),
            is_primary=make_primary,
        )
    )
    db.commit()
    flash(request, "联系人已添加")
    return redirect(f"/customers/{customer_id}")


@router.post("/{customer_id}/contacts/{contact_id}/delete")
def contact_delete(
    customer_id: int,
    contact_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.customer_id == customer_id)
    )
    if contact:
        db.delete(contact)
        db.commit()
        flash(request, "联系人已删除")
    return redirect(f"/customers/{customer_id}")

