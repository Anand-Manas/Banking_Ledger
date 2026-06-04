from fastapi import FastAPI
from app.api.routers import auth, admin, customer, transactions, beneficiaries
from app.api.routers.health import router as health_router
from app.core.logging import logger

app = FastAPI(
    title="Core Banking System",
    description="""
    A production-grade Core Banking backend built using FastAPI.

    Key features:
    - Secure JWT authentication with multi-role support
    - Admin-controlled account lifecycle and customer management
    - Atomic money transfers with account number resolution
    - Customer credit request workflow with admin approval
    - Controlled overdraft
    - Redis caching (read-only)
    - Audit logging for sensitive operations
    """,
    version="2.0.0",
)

logger.info("Application started")

app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(customer.router, prefix="/customer", tags=["Customer"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["Beneficiaries"])