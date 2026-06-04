#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
  echo ""
  echo "Shutting down development environment..."
  docker compose down
  echo "Done."
}
trap cleanup EXIT INT TERM

echo "Starting dev infrastructure (backend + minio)..."
COMPOSE_PROFILES=dev docker compose up -d --build

echo "Waiting for backend to be ready..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
  sleep 1
done
echo "Backend is ready."

echo "Starting frontend dev server..."
cd frontend && npm run dev
