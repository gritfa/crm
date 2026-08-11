"""Create fictional demo records for local evaluation only."""

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Contract, Customer, Lead, Payment, User  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        raise SystemExit("安全保护：演示数据脚本只允许写入 SQLite 数据库")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.phone == settings.ADMIN_PHONE))
        if not admin:
            admin = User(
                name=settings.ADMIN_NAME,
                phone=settings.ADMIN_PHONE,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.flush()

        customer = db.scalar(select(Customer).where(Customer.name == "示例星河科技"))
        if not customer:
            customer = Customer(
                name="示例星河科技",
                contact_name="示例联系人",
                phone="13900000001",
                source="示例转介绍",
                notes="此记录为虚构演示数据，可以安全删除。",
                owner_id=admin.id,
            )
            db.add(customer)
            db.flush()

        if not db.scalar(select(Lead.id).where(Lead.name == "示例晨光工作室")):
            db.add(
                Lead(
                    name="示例晨光工作室",
                    phone="13900000002",
                    source="示例官网咨询",
                    status="following",
                    next_follow_at=date.today() + timedelta(days=2),
                    notes="虚构线索：确认服务范围并发送报价。",
                    owner_id=admin.id,
                )
            )

        contract = db.scalar(select(Contract).where(Contract.number == "DEMO-2026-001"))
        if not contract:
            contract = Contract(
                number="DEMO-2026-001",
                customer_id=customer.id,
                title="示例年度顾问服务",
                amount=Decimal("12000.00"),
                status="active",
                start_date=date.today().replace(day=1),
                notes="虚构合同，仅用于本地演示。",
                owner_id=admin.id,
            )
            db.add(contract)
            db.flush()

        if not db.scalar(select(Payment.id).where(Payment.reference == "DEMO-PAY-001")):
            db.add(
                Payment(
                    contract_id=contract.id,
                    amount=Decimal("3000.00"),
                    paid_on=date.today(),
                    method="bank",
                    reference="DEMO-PAY-001",
                    notes="虚构收款记录",
                    recorded_by_id=admin.id,
                )
            )
        db.commit()

    print("虚构演示数据已创建。")


if __name__ == "__main__":
    main()

