# G9 — Idle Reaper Validation (R7)

**Report date:** 2026-06-08
**Phase:** 3 (P3)
**Subject:** RuntimeManager.run_idle_reaper
**Status:** Architecture-validated
**Result:** PASS

---

## Scope

This report validates the idle reaper (R7): a runtime
that has been Active but has not served a request for
longer than its descriptor's
`spec.lifecycle.idle_timeout` is auto-stopped. The
container is preserved (image is local); subsequent
requests trigger re-activation (warm or cold start).

## Vocabulary

`spec.lifecycle.idle_timeout` is a closed set:

| Value | Meaning | Default for |
|-------|---------|-------------|
| `never` | Autoscaler owns lifecycle | Cloud (future) |
| `15m`  | 15 minutes of inactivity | Community Edition |
| `30m`  | 30 minutes of inactivity | (operator) |
| `1h`   | 1 hour of inactivity | (operator) |
| `6h`   | 6 hours of inactivity | (operator) |

The Kokoro runtime descriptor declares `idle_timeout: "15m"`.
Any other value is rejected at descriptor load time
(see `test_runtime_lifecycle_idle_timeout.py`).

## Test surface

### Architecture-validated (in repo)

`backend/tests/test_runtime_idle_reaper.py` (6 tests, all pass):

1. **Active idle > timeout is auto-stopped.**
   An Active instance whose `last_request_at` is 30
   minutes ago is auto-stopped by the reaper; `stop_runtime`
   is called on the driver; the `RuntimeIdleTimeout` event
   is emitted.

2. **Active with no `last_request_at` is not reaped.**
   The runtime may have been started manually outside the
   manager (e.g. by an operator via docker CLI). Without a
   recorded `last_request_at`, the reaper has no signal to
   stop it. This avoids accidental stops of operator-started
   runtimes.

3. **Active with recent `last_request_at` is not reaped.**
   An instance that was touched 5 minutes ago (timeout=15m)
   is not reaped. The reaper respects the threshold.

4. **`idle_timeout = "never"` disables the reaper.**
   The Cloud default. The autoscaler owns lifecycle; the
   backend reaper never stops a runtime with `idle_timeout = "never"`,
   even if `last_request_at` is ancient.

5. **Non-Active states (Installed/Stopped/Failed) are skipped.**
   The reaper only considers `Active` instances. An
   `Installed` or `Stopped` instance is left alone.

6. **The `RuntimeIdleTimeout` event reports elapsed seconds.**
   The event carries `runtime_id` and `idle_seconds`. The
   reaper test asserts `~20 minutes = ~1200 seconds` (±5s
   for test latency).

### Wiring-validated (in repo)

`backend/tests/test_runtime_wiring.py` (8 tests) verifies:
- The idle reaper background task is started when
  `RUNTIME_SERVICE_ENABLED=true`.
- The task is cancelled on shutdown.
- The reaper never runs at startup (R6 — lazy activation);
  the first `run_idle_reaper()` invocation is the first
  reaper cycle.

## Reaper contract

```
RUNTIME_MANAGER.run_idle_reaper() -> int
  for runtime_id, inst in _instance_cache.items():
    if inst.state != ACTIVE: skip
    if inst.last_request_at is None: skip  # manually started
    timeout_seconds = parse_idle_timeout_to_seconds(descriptor.lifecycle.idle_timeout)
    if timeout_seconds is None: skip       # "never"
    if (now - last_request_at).total_seconds() < timeout_seconds: skip
    await self.stop(runtime_id)            # auto-stop
    events.publish(RuntimeIdleTimeout(runtime_id, idle_seconds))
  return count_reaped
```

The reaper is **idempotent** within a single cycle: a
runtime is reaped at most once. The reaper is **safe under
concurrent calls**: the manager's instance cache is
single-threaded within a process.

## Background task

`backend/app/services/runtime_wiring.py` provides:

```python
async def start_idle_reaper(manager) -> asyncio.Task | None
async def stop_idle_reaper(task) -> None
```

`start_idle_reaper` creates a coroutine that wakes up
every 60 seconds and calls `manager.run_idle_reaper()`
once. `stop_idle_reaper` cancels the task on shutdown
(in `main.py` lifespan's `finally` block).

The reaper is **opt-in**: when
`RUNTIME_SERVICE_ENABLED=false`, no task is created. The
in-process adapter path is the only path; runtime lifecycle
is the operator's responsibility.

## Result

- Architecture-validated: **PASS** (6 reaper tests + 8 wiring tests).
- Reaper contract: documented.
- Background task: wired into `main.py` lifespan.

This report closes G9 of the Phase 3 validation plan
(see
[`VALIDATION.md` § Phase 3 G9](../SPECS/FEATURES/runtime-services-implementation/VALIDATION.md)).

---

**See also:**
[`SPECS/FEATURES/runtime-services-implementation/VALIDATION.md` § G9](../SPECS/FEATURES/runtime-services-implementation/VALIDATION.md)
·
[`DESIGN.md` §3.4 + §9.4](../SPECS/FEATURES/runtime-services-implementation/DESIGN.md)
·
[`tests/test_runtime_idle_reaper.py`](../../../tests/test_runtime_idle_reaper.py)
