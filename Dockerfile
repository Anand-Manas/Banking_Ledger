FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2 compilation (if needed) and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run migrations, create admin, start server
CMD ["sh", "-c", "python -c 'from app.db.init_db import init_db; init_db()' && python admin_creation.py && uvicorn app.app:app --host 0.0.0.0 --port 8000"]