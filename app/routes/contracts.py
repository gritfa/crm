from fastapi import APIRouter, Form, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from app.forms import optional, parse_amount, parse_date, required
from app.models import Contract, Customer
from app.security import validate_csrf
from app.web import flash, redirect, render


router = APIRouter()


@router.get("")
def contract_list(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    q: str = "",
    status: str = "all",
):
    stmt = (
        select(Contract)
        .options(selectinload(Contract.customer), selectinload(Contract.payments))
        .order_by(Contract.updated_at.desc())
    )
    if q.strip():
        keyword = f"%{q.strip()}%"
        stmt = stmt.join(Customer).where(
            or_(Contract.number.ilike(keyword), Contract.title.ilike(keyword), Customer.name.ilike(keyword))
        )
    if status in {"draft", "active", "completed", "cancelled"}:
        stmt = stmt.where(Contract.status == status)
    contracts = db.scalars(stmt).unique().all()
    return render(
        request,
        "contracts/list.html",
        user=user,
        contracts=contracts,
        q=q,
        status=status,
    )


@router.get("/new")
def contract_new(request: Request, db: DbSession, user: CurrentUser, customer_id: int | None = None):
    customers = db.scalars(select(Customer).where(Customer.status == "active").order_by(Customer.name)).all()
    return render(
        request,
        "contracts/form.html",
        user=user,
        contract=None,
        customers=customers,
        selected_customer_id=customer_id,
    )


@router.post("")
def contract_create(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    number: str = Form(...),
    customer_id: int = Form(...),
    title: str = Form(...),
    amount: str = Form("0"),
    status: str = Form("draft"),
    start_date: str = Form(""),
    end_date: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    number = required(number, "合同编号")
    if db.scalar(select(Contract.id).where(Contract.number == number)):
        flash(request, "合同编号已存在", "danger")
        return redirect("/contracts/new")
    if not db.get(Customer, customer_id):
        flash(request, "客户不存在", "danger")
        return redirect("/contracts/new")
    contract = Contract(
        number=number,
        customer_id=customer_id,
        title=required(title, "合同名称"),
        amount=parse_amount(amount),
        status=status if status in {"draft", "active"} else "draft",
        start_date=parse_date(start_date, "开始日期"),
        end_date=parse_date(end_date, "结束日期"),
        notes=optional(notes),
        owner_id=user.id,
    )
    db.add(contract)
    db.commit()
    flash(request, "合同创建成功")
    return redirect("/contracts")


@router.get("/{contract_id}/edit")
def contract_edit(contract_id: int, request: Request, db: DbSession, user: CurrentUser):
    contract = db.get(Contract, contract_id)
    if not contract:
        flash(request, "合同不存在", "danger")
        return redirect("/contracts")
    customers = db.scalars(select(Customer).order_by(Customer.name)).all()
    return render(
        request,
        "contracts/form.html",
        user=user,
        contract=contract,
        customers=customers,
        selected_customer_id=contract.customer_id,
    )


@router.post("/{contract_id}")
def contract_update(
    contract_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    number: str = Form(...),
    customer_id: int = Form(...),
    title: str = Form(...),
    amount: str = Form("0"),
    status: str = Form("draft"),
    start_date: str = Form(""),
    end_date: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    contract = db.get(Contract, contract_id)
    if not contract:
        flash(request, "合同不存在", "danger")
        return redirect("/contracts")
    cleaned_number = required(number, "合同编号")
    duplicate = db.scalar(
        select(Contract.id).where(Contract.number == cleaned_number, Contract.id != contract_id)
    )
    if duplicate:
        flash(request, "合同编号已存在", "danger")
        return redirect(f"/contracts/{contract_id}/edit")
    if not db.get(Customer, customer_id):
        flash(request, "客户不存在", "danger")
        return redirect(f"/contracts/{contract_id}/edit")
    contract.number = cleaned_number
    contract.customer_id = customer_id
    contract.title = required(title, "合同名称")
    contract.amount = parse_amount(amount)
    contract.status = status if status in {"draft", "active", "completed", "cancelled"} else "draft"
    contract.start_date = parse_date(start_date, "开始日期")
    contract.end_date = parse_date(end_date, "结束日期")
    contract.notes = optional(notes)
    db.commit()
    flash(request, "合同已更新")
    return redirect("/contracts")
