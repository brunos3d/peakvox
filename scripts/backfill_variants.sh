#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if command -v docker &>/dev/null && docker compose ls &>/dev/null 2>&1; then
  echo "Running backfill via Docker..."
  docker compose exec -T backend mkdir -p /app/scripts
  docker compose cp "$SCRIPT_DIR/backfill_variants.py" backend:/app/scripts/backfill_variants.py
  docker compose exec -T backend python /app/scripts/backfill_variants.py "$@"
  docker compose exec -T backend rm -rf /app/scripts
else
  echo "Running backfill directly (requires backend venv)..."
  if [ -f "$PROJECT_DIR/backend/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/backend/.venv/bin/activate"
  fi
  cd "$PROJECT_DIR"
  PYTHONPATH="$PROJECT_DIR/backend:$PYTHONPATH" \
    python scripts/backfill_variants.py "$@"
fi
