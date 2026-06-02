from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional, List
from decimal import Decimal
from uuid import UUID

class CreateAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr

class CreateCustomerRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    address: Optional[str] = None
    customer_type: Literal["INDIVIDUAL", "CORPORATE"]

class CreateAccountRequest(BaseModel):
    customer_id: UUID
    account_type: Literal["SAVINGS", "CURRENT"]
    overdraft_limit: Decimal = Decimal("0")

class CreditRequest(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)

class CustomerListItem(BaseModel):
    customer_id: str
    full_name: str
    email: str
    phone: str
    customer_type: str
    account_count: int
    total_balance: str
    status: str

class CustomerAccountDetail(BaseModel):
    account_id: str
    account_number: str
    account_type: str
    balance: str
    status: str
    overdraft_limit: str

class CustomerTransactionDetail(BaseModel):
    transaction_id: str
    type: str
    amount: str
    status: str
    timestamp: Optional[str]

class CustomerDetailResponse(BaseModel):
    customer_id: str
    full_name: str
    email: str
    phone: str
    customer_type: str
    address: Optional[str]
    created_at: Optional[str]
    accounts: List[CustomerAccountDetail]
    recent_transactions: List[CustomerTransactionDetail]
