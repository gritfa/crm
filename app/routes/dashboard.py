from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import Contract, Customer, Lead, Payment
from app.web import render


router = APIRouter()


@router.get("/")
def dashboard(request: Request, db: DbSession, user: CurrentUser):
    today = date.today()
    month_start = today.replace(day=1)
    stats = {
        "customers": db.scalar(select(func.count(Customer.id)).where(Customer.status == "active")) or 0,
        "open_leads": db.scalar(
            select(func.count(Lead.id)).where(Lead.status.in_(["new", "following"]))
        )
        or 0,
        "active_contracts": db.scalar(
            select(func.count(Contract.id)).where(Contract.status == "active")
        )
        or 0,
        "month_payments": db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.paid_on >= month_start)
        )
        or Decimal("0"),
    }
    recent_payments = db.scalars(
        select(Payment).order_by(Payment.paid_on.desc(), Payment.id.desc()).limit(8)
    ).all()
    followups = db.scalars(
        select(Lead)
        .where(Lead.status.in_(["new", "following"]), Lead.next_follow_at.is_not(None))
        .order_by(Lead.next_follow_at.asc())
        .limit(8)
    ).all()
    return render(
        request,
        "dashboard.html",
        user=user,
        stats=stats,
        recent_payments=recent_payments,
        followups=followups,
        today=today,
    )

