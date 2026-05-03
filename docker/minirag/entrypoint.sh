#!/bin/bash
set -e
##stop if any command fails

echo "Running database migrations..."
cd /app/models/db_schemes/minirag/
# Run database migrations
alembic upgrade head
cd /app

echo "Starting application..."
exec "$@"  # ✅ this executes the CMD arguments