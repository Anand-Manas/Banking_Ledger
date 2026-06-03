from app.db.base import Base
from app.db.session import engine

# Import ALL models so Base.metadata knows about them
from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.models.transaction_model import Transaction
from app.models.credit_request import CreditRequest
from app.models.audit_log import AuditLog
from app.models.beneficiary_model import Beneficiary

def init_db():
    Base.metadata.create_all(bind=engine)