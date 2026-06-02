from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

class CustomerCreditRequestCreate(BaseModel):
    account_id: str
    amount: Decimal = Field(..., gt=0)
    customer_note: Optional[str] = None

class CustomerCreditRequestResponse(BaseModel):
    request_id: str
    account_number: str
    amount: str
    status: str
    customer_note: Optional[str]
    admin_note: Optional[str]
    requested_at: str
    processed_at: Optional[str]

class AdminCreditRequestListItem(BaseModel):
    request_id: str
    customer_name: str
    customer_id: str
    account_number: str
    amount: str
    customer_note: Optional[str]
    requested_at: str

class AdminCreditRequestAction(BaseModel):
    admin_note: Optional[str] = None
