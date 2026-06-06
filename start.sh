$startSh = @'
#!/bin/sh
set -e

echo "=== Railway Startup Debug ==="
echo "PORT=$PORT"
echo "DATABASE_URL exists: $(if [ -n "$DATABASE_URL" ]; then echo 'YES'; else echo 'NO'; fi)"
echo "PWD=$(pwd)"
echo "Files in /app: $(ls -la /app)"

# Run migrations best-effort (don't block startup)
if [ -f alembic.ini ] && [ -d alembic/versions ] && [ "$(ls -A alembic/versions)" ]; then
    echo "=== Running Alembic migrations ==="
    alembic upgrade head || echo "WARNING: Alembic migration failed, continuing..."
else
    echo "=== No Alembic migrations found, skipping ==="
fi

# Start Uvicorn
echo "=== Starting Uvicorn on port ${PORT:-8000} ==="
exec uvicorn app.app:app --host 0.0.0.0 --port "${PORT:-8000}"
'@

$startSh | Out-File -FilePath start.sh -Encoding utf8 -NoNewline