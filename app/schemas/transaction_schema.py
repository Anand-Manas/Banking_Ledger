from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_number: str
    amount: Decimal = Field(..., gt=0)
    idempotency_key: str

class TransactionEntry(BaseModel):
    transaction_id: UUID
    type: str
    amount: Decimal
    related_account: Optional[UUID] = None
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True

class MiniStatementResponse(BaseModel):
    account_id: UUID
    current_balance: Decimal
    transactions: List[TransactionEntry]
