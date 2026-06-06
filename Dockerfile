FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE BUST: forces Railway to rebuild from this layer
RUN echo "cache-bust-2026-06-06-001"

COPY . .

EXPOSE 8000

CMD ["python", "startup.py"]