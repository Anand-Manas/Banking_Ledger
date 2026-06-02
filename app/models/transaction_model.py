from sqlalchemy import Column, Enum, TIMESTAMP, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("customer_id", "idempotency_key", name="uq_customer_idempotency"),
    )

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.account_id"))
    destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.account_id"))
    transaction_type = Column(
        Enum("TRANSFER", "CREDIT", "DEBIT", name="transaction_types"),
        nullable=False
    )
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(Enum("PENDING", "SUCCESS", "FAILED", name="transaction_status"), nullable=False)
    idempotency_key = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
