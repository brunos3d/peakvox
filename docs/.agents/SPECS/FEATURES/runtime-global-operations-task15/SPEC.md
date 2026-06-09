# SPEC — Runtime Global Operations (Task 15)

## Objective
Make runtime lifecycle operations backend-owned, globally visible, and multi-session safe.

## Scope
- Introduce backend RuntimeOperation tracking for install/update/start/stop/remove/build.
- Expose operation status via runtime API.
- Drive frontend lifecycle rendering from backend operation + runtime state.
- Validate multi-tab consistency via browser workflow.

## Non-Goals
- Provider-specific runtime image fixes (tracked separately).
- Re-architecting Runtime Registry descriptor schema beyond operation metadata needs.

## Acceptance Criteria
- Operation state is backend authoritative.
- Two browser tabs reflect the same in-flight operation state.
- Page refresh preserves operation visibility.
- Failures expose meaningful backend-provided messages.
- Cancellation endpoint exists and behaves safely when supported.
