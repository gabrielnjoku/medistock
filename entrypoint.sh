#!/bin/sh
set -e

echo "=== MediStock Container Startup ==="
echo "Running Alembic database migrations..."
alembic upgrade head || {
    echo "Warning: Alembic migration failed or DB already up to date."
}

echo "Starting Uvicorn web server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
