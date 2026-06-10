#!/usr/bin/env bash
# Development environment with hot reload for backend and frontend.
#
#   scripts/start-dev.sh            start everything (no image rebuilds)
#   scripts/start-dev.sh --build    rebuild the backend image first
#                                   (only needed when backend/requirements.txt
#                                   or backend/Dockerfile changed)
#
# Backend + MinIO run in Docker (the backend needs the Docker socket and the
# shared /data volume for the Runtime Registry). backend/app is bind-mounted
# into the container and uvicorn runs with --reload, so Python changes apply
# on save. The frontend runs on the host via `next dev` for native HMR.
# Ctrl-C stops the frontend and brings the compose services down. Runtime
# containers (peakvox-runtime-*) are driver-managed and are never touched.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev)

cleanup() {
  echo ""
  echo "Shutting down development environment..."
  "${COMPOSE[@]}" down
  echo "Done."
}
trap cleanup EXIT INT TERM

if [[ "${1:-}" == "--build" ]]; then
  echo "Rebuilding backend image (requirements/Dockerfile change)..."
  "${COMPOSE[@]}" build backend
fi

# The production frontend container binds :3000; in dev the frontend runs on
# the host, so stop it if a previous production run left it up.
docker compose stop frontend >/dev/null 2>&1 || true

echo "Starting dev infrastructure (backend + minio, hot reload enabled)..."
"${COMPOSE[@]}" up -d

echo "Waiting for backend to be ready..."
for _ in $(seq 1 120); do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
  echo "Backend did not become ready within 120s. Logs:" >&2
  "${COMPOSE[@]}" logs --tail 50 backend >&2
  exit 1
fi
echo "Backend is ready (http://localhost:8000 — reloads on save in backend/app/)."

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

echo "Starting frontend dev server (http://localhost:3000 — HMR on save)..."
cd frontend && npm run dev
