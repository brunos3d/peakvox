"""In-memory capture of runtime install (docker build / pull) terminal output.

The `DockerRuntimeDriver` streams the underlying `docker build` / `docker pull`
output line-by-line into a per-runtime ring buffer here; the Models page
"Check Logs" dialog polls `GET /api/runtimes/{id}/install-logs` to show advanced
users the real image build progress instead of only the coarse
"Pulling runtime image (30%)" step text.

Design notes:
- **Dependency-light, docker-free** so it can be imported by the API layer
  without crossing the "no docker outside the driver" boundary
  (`tests/test_lint_no_docker_outside_driver.py`). Only the driver writes to it;
  the API only reads.
- **Thread-safe.** The driver's `_install_image` runs in a worker thread
  (`asyncio.to_thread`), so appends happen off the event loop while the API
  reads from it on the loop. A single lock guards all access.
- **Bounded.** Each runtime keeps at most `_MAX_LINES` of scrollback so a long
  build (thousands of layer lines) can't grow without limit.
- **Ephemeral.** Logs live for the process lifetime; they are operational
  output, not persisted history. A new install for the same runtime resets it.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

_MAX_LINES = 4000


@dataclass
class _RuntimeLog:
    lines: Deque[str] = field(default_factory=lambda: deque(maxlen=_MAX_LINES))
    active: bool = False
    ok: Optional[bool] = None
    error: Optional[str] = None
    # Monotonic-ish counter so the frontend can cheaply detect "no new output".
    seq: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


_logs: Dict[str, _RuntimeLog] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start(runtime_id: str, header: Optional[str] = None) -> None:
    """Begin a fresh capture for a runtime install/update, clearing prior output."""
    with _lock:
        entry = _RuntimeLog()
        entry.active = True
        entry.started_at = _now()
        if header:
            entry.lines.append(header)
            entry.seq += 1
        _logs[runtime_id] = entry


def append(runtime_id: str, text: str) -> None:
    """Append raw build/pull output. Splits on newlines and drops blank trailers."""
    if not text:
        return
    with _lock:
        entry = _logs.get(runtime_id)
        if entry is None:
            entry = _RuntimeLog(active=True, started_at=_now())
            _logs[runtime_id] = entry
        for raw in text.splitlines():
            line = raw.rstrip("\r")
            if line == "" and (not entry.lines or entry.lines[-1] == ""):
                # Collapse runs of blank lines (docker emits many).
                continue
            entry.lines.append(line)
            entry.seq += 1


def finish(runtime_id: str, ok: bool, error: Optional[str] = None) -> None:
    """Mark the capture complete (success or failure) and append a footer."""
    with _lock:
        entry = _logs.get(runtime_id)
        if entry is None:
            entry = _RuntimeLog()
            _logs[runtime_id] = entry
        entry.active = False
        entry.ok = ok
        entry.error = error
        entry.finished_at = _now()
        footer = "✓ install completed" if ok else f"✗ install failed: {error or 'unknown error'}"
        entry.lines.append(footer)
        entry.seq += 1


def snapshot(runtime_id: str) -> dict:
    """Read the current buffer for the API. Returns an empty inactive snapshot
    for a runtime that was never installed in this process."""
    with _lock:
        entry = _logs.get(runtime_id)
        if entry is None:
            return {
                "runtime_id": runtime_id,
                "lines": [],
                "active": False,
                "ok": None,
                "error": None,
                "seq": 0,
                "started_at": None,
                "finished_at": None,
            }
        lines: List[str] = list(entry.lines)
        return {
            "runtime_id": runtime_id,
            "lines": lines,
            "active": entry.active,
            "ok": entry.ok,
            "error": entry.error,
            "seq": entry.seq,
            "started_at": entry.started_at,
            "finished_at": entry.finished_at,
        }


def reset(runtime_id: str) -> None:
    """Drop a runtime's buffer (e.g. on remove). Safe if absent."""
    with _lock:
        _logs.pop(runtime_id, None)
