#!/bin/bash
set -e

echo "Creating data directories..."
python -c "from app.core.config import settings; settings.create_dirs()"

echo "Initializing database..."
python -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
print('Database initialized.')
"

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
