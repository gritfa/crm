from datetime import date

from fastapi import APIRouter, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from app.forms import optional, parse_amount, parse_date
from app.models import Contract, Payment
from app.security import validate_csrf
from app.web import flash, redirect, render


router = APIRouter()


@router.get("")
def payment_list(request: Request, db: DbSession, user: CurrentUser):
    payments = db.scalars(
        select(Payment)
        .options(selectinload(Payment.contract).selectinload(Contract.customer))
        .order_by(Payment.paid_on.desc(), Payment.id.desc())
    ).all()
    return render(request, "payments/list.html", user=user, payments=payments)


@router.get("/new")
def payment_new(request: Request, db: DbSession, user: CurrentUser, contract_id: int | None = None):
    contracts = db.scalars(
        select(Contract)
        .where(Contract.status.in_(["draft", "active"]))
        .options(selectinload(Contract.customer), selectinload(Contract.payments))
        .order_by(Contract.created_at.desc())
    ).all()
    return render(
        request,
        "payments/form.html",
        user=user,
        contracts=contracts,
        selected_contract_id=contract_id,
        today=date.today(),
    )


@router.post("")
def payment_create(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    contract_id: int = Form(...),
    amount: str = Form(...),
    paid_on: str = Form(...),
    method: str = Form("bank"),
    reference: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    contract = db.get(Contract, contract_id)
    if not contract:
        flash(request, "合同不存在", "danger")
        return redirect("/payments/new")
    payment = Payment(
        contract_id=contract_id,
        amount=parse_amount(amount, positive=True),
        paid_on=parse_date(paid_on, "收款日期") or date.today(),
        method=method if method in {"bank", "cash", "wechat", "alipay", "other"} else "other",
        reference=optional(reference),
        notes=optional(notes),
        recorded_by_id=user.id,
    )
    db.add(payment)
    if contract.status == "draft":
        contract.status = "active"
    db.commit()
    flash(request, "收款登记成功")
    return redirect("/payments")


@router.post("/{payment_id}/delete")
def payment_delete(
    payment_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    payment = db.get(Payment, payment_id)
    if payment:
        db.delete(payment)
        db.commit()
        flash(request, "收款记录已删除")
    return redirect("/payments")

