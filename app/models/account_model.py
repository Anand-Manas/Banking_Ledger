from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False
    )
    account_number = Column(String(20), unique=True, nullable=False)
    account_type = Column(
        Enum("SAVINGS", "CURRENT", name="account_types"),
        nullable=False
    )
    balance = Column(Numeric(15, 2), nullable=False, default=0)
    min_balance = Column(Numeric(15, 2), default=0)
    status = Column(
        Enum("ACTIVE", "FROZEN", "CLOSED", name="account_status"),
        default="ACTIVE"
    )
    overdraft_limit = Column(Numeric(15, 2), default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
