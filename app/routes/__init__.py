from fastapi import APIRouter

from app.routes import auth, contracts, customers, dashboard, leads, payments, users


router = APIRouter()
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(users.router, prefix="/users")
router.include_router(customers.router, prefix="/customers")
router.include_router(leads.router, prefix="/leads")
router.include_router(contracts.router, prefix="/contracts")
router.include_router(payments.router, prefix="/payments")

