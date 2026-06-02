from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    beneficiary_account_number = Column(String(20), nullable=False)
    bank_name = Column(String(100))
    status = Column(Enum("ACTIVE", "INACTIVE", name="beneficiary_status"), default="ACTIVE")
    created_at = Column(TIMESTAMP, server_default=func.now())
