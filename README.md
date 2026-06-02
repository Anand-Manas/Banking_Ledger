# Core Banking Ledger

A production-grade Core Banking backend built with **FastAPI**, **PostgreSQL**, **Redis**, and **SQLAlchemy 2.0**.

## Features

- **JWT Authentication** — Secure login with multi-role support (Admin + Customer per user)
- **Admin-Controlled Lifecycle** — Admins create customers, accounts, and approve credit requests
- **Atomic Money Transfers** — Row-level locking with deadlock prevention via deterministic lock ordering
- **Account Number Resolution** — Transfer by human-readable account numbers, not UUIDs
- **Credit Request Workflow** — Customers request credits, admins approve/reject with audit trail
- **Idempotency Keys** — Duplicate request protection for transfers
- **Overdraft Control** — Configurable overdraft limits per account
- **Audit Logging** — Every sensitive operation is logged
- **Redis Caching** — Read-through cache for account data with invalidation
- **Pydantic v2** — Strict request/response validation

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd Banking-Ledger
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env with your database and Redis credentials
```

### 3. Database Setup

```bash
createdb banking
python -c "from app.db.init_db import init_db; init_db()"
```

### 4. Create Admin User

```bash
export ADMIN_PASSWORD="your-secure-password"
python admin_creation.py
```

### 5. Run the Server

```bash
python main.py
```

API docs available at: `http://localhost:8000/docs`

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register new customer |
| POST | `/auth/login` | — | Login, get JWT token |
| POST | `/admin/admins` | Admin | Create new admin |
| GET | `/admin/customers` | Admin | List all customers |
| GET | `/admin/customers/{id}` | Admin | Customer details + accounts + transactions |
| POST | `/admin/customers` | Admin | Create customer |
| POST | `/admin/accounts` | Admin | Create account |
| POST | `/admin/credit` | Admin | Credit an account directly |
| GET | `/admin/credit-requests` | Admin | List pending credit requests |
| POST | `/admin/credit-requests/{id}/approve` | Admin | Approve credit request |
| POST | `/admin/credit-requests/{id}/reject` | Admin | Reject credit request |
| GET | `/customer/profile` | Customer | Get customer profile |
| GET | `/customer/accounts` | Customer | List accounts |
| GET | `/customer/accounts/{id}` | Customer | Account details |
| POST | `/customer/credit-requests` | Customer | Request account credit |
| GET | `/customer/credit-requests` | Customer | List my credit requests |
| POST | `/transactions/transfer` | Customer | Transfer money |
| GET | `/transactions/statement/{id}` | Customer | Mini statement |
| POST | `/beneficiaries/` | Customer | Add beneficiary |
| GET | `/beneficiaries/` | Customer | List beneficiaries |

## Testing

```bash
pytest tests/test_transfers.py -v
pytest tests/test_credit_requests.py -v
python tests/test_concurrency.py
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.109 |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Auth | JWT (python-jose) + bcrypt |
| Testing | pytest |
