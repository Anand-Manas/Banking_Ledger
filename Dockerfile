FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use semicolons instead of && so alembic failure never blocks uvicorn
# ${PORT:-8000} defaults to 8000 if PORT is not set
CMD ["sh", "-c", "echo '=== Railway Startup ==='; echo PORT=$PORT; echo DATABASE_URL=$(echo $DATABASE_URL | cut -c1-50)...; alembic upgrade head 2>/dev/null || echo 'Migrations skipped or failed'; exec uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-8000}"]