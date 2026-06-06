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

# Debug: print env vars, then run migrations if alembic exists, then start app
CMD ["sh", "-c", "echo '--- ENV DEBUG ---' && echo DATABASE_URL=$DATABASE_URL && echo PORT=$PORT && echo '--- STARTING ---' && if [ -f alembic.ini ] && [ -d alembic/versions ] && [ \"$(ls -A alembic/versions)\" ]; then alembic upgrade head; else echo 'No migrations found, skipping alembic'; fi && uvicorn app.app:app --host 0.0.0.0 --port ${PORT:-8000}"]