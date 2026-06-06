# ---------- Build Stage ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps for psycopg2 + asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- Runtime Stage ----------
FROM python:3.11-slim

WORKDIR /app

# Copy only runtime Python packages
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install libpq runtime only (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000

# Railway sets $PORT at runtime; default to 8000 for local Docker
CMD sh -c "if [ -f alembic.ini ]; then alembic upgrade head; fi && uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-8000}"