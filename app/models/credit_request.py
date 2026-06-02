from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class CreditRequest(Base):
    __tablename__ = "credit_requests"

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.account_id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(Enum("PENDING", "APPROVED", "REJECTED", name="credit_request_status"), default="PENDING")
    customer_note = Column(String(255))
    admin_note = Column(String(255))
    requested_at = Column(TIMESTAMP, server_default=func.now())
    processed_at = Column(TIMESTAMP)
    processed_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
