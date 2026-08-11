from fastapi import APIRouter, Form, Request
from sqlalchemy import or_, select

from app.dependencies import CurrentUser, DbSession
from app.forms import optional, parse_date, required
from app.models import Customer, Lead
from app.security import validate_csrf
from app.web import flash, redirect, render


router = APIRouter()


@router.get("")
def lead_list(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = "",
    status: str = "open",
):
    stmt = select(Lead).order_by(Lead.updated_at.desc())
    if q.strip():
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(or_(Lead.name.ilike(keyword), Lead.phone.ilike(keyword)))
    if status == "open":
        stmt = stmt.where(Lead.status.in_(["new", "following"]))
    elif status in {"new", "following", "won", "lost"}:
        stmt = stmt.where(Lead.status == status)
    leads = db.scalars(stmt).all()
    return render(request, "leads/list.html", user=user, leads=leads, q=q, status=status)


@router.get("/new")
def lead_new(request: Request, user: CurrentUser):
    return render(request, "leads/form.html", user=user, lead=None)


@router.post("")
def lead_create(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(...),
    phone: str = Form(""),
    source: str = Form(""),
    next_follow_at: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    lead = Lead(
        name=required(name, "线索名称"),
        phone=optional(phone),
        source=optional(source),
        next_follow_at=parse_date(next_follow_at, "下次跟进日期"),
        notes=optional(notes),
        owner_id=user.id,
    )
    db.add(lead)
    db.commit()
    flash(request, "线索创建成功")
    return redirect("/leads")


@router.get("/{lead_id}/edit")
def lead_edit(lead_id: int, request: Request, db: DbSession, user: CurrentUser):
    lead = db.get(Lead, lead_id)
    if not lead:
        flash(request, "线索不存在", "danger")
        return redirect("/leads")
    return render(request, "leads/form.html", user=user, lead=lead)


@router.post("/{lead_id}")
def lead_update(
    lead_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: str = Form(...),
    phone: str = Form(""),
    source: str = Form(""),
    status: str = Form("new"),
    next_follow_at: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    lead = db.get(Lead, lead_id)
    if not lead:
        flash(request, "线索不存在", "danger")
        return redirect("/leads")
    lead.name = required(name, "线索名称")
    lead.phone = optional(phone)
    lead.source = optional(source)
    if lead.status != "won":
        lead.status = status if status in {"new", "following", "lost"} else "new"
    lead.next_follow_at = parse_date(next_follow_at, "下次跟进日期")
    lead.notes = optional(notes)
    db.commit()
    flash(request, "线索已更新")
    return redirect("/leads")


@router.post("/{lead_id}/convert")
def lead_convert(
    lead_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    lead = db.get(Lead, lead_id)
    if not lead:
        flash(request, "线索不存在", "danger")
        return redirect("/leads")
    if lead.converted_customer_id:
        return redirect(f"/customers/{lead.converted_customer_id}")
    base_name = lead.name
    name = base_name
    suffix = 2
    while db.scalar(select(Customer.id).where(Customer.name == name)):
        name = f"{base_name} ({suffix})"
        suffix += 1
    customer = Customer(
        name=name,
        contact_name=lead.name,
        phone=lead.phone,
        source=lead.source,
        notes=lead.notes,
        owner_id=lead.owner_id or user.id,
    )
    db.add(customer)
    db.flush()
    lead.status = "won"
    lead.converted_customer_id = customer.id
    db.commit()
    flash(request, "线索已转为客户")
    return redirect(f"/customers/{customer.id}")

