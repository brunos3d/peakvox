# DESIGN — Runtime Global Operations (Task 15)

## Architecture
RuntimeManager owns a per-runtime operation record and optional background task.

Flow:
Runtime API action -> RuntimeManager.begin_operation -> driver call -> operation status updates -> Runtime state cache update -> API/UI polling reflects progress.

## Operation Model
Fields:
- id
- runtime_id
- type
- status
- progress
- message
- started_at
- updated_at
- cancellable

## API Surface
- GET /api/runtimes/{id}/operation
- GET /api/runtime-operations
- POST /api/runtimes/{id}/operations/{operation_id}/cancel

## Frontend Sync
React Query polls operation endpoints and composed runtime state.
Operation phases override button availability and labels.
