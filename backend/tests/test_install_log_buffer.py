"""Tests for the install-log buffer (Models page "Check Logs" feature).

The DockerRuntimeDriver streams docker build/pull output into this buffer; the
API serves it via GET /api/runtimes/{id}/install-logs. The buffer is docker-free
(must stay importable by the API without crossing the no-docker boundary),
thread-safe, bounded, and resets per install.
"""

from __future__ import annotations

import threading

from app.services import install_log_buffer as buf


def setup_function() -> None:
    buf.reset("rt")


def test_snapshot_empty_for_unknown_runtime() -> None:
    snap = buf.snapshot("never-installed")
    assert snap["lines"] == []
    assert snap["active"] is False
    assert snap["ok"] is None
    assert snap["seq"] == 0


def test_start_append_finish_success() -> None:
    buf.start("rt", header="$ install rt")
    buf.append("rt", "Step 1/2 : FROM base\nStep 2/2 : RUN pip install\n")
    buf.finish("rt", ok=True)
    snap = buf.snapshot("rt")
    assert snap["lines"][0] == "$ install rt"
    assert "Step 1/2 : FROM base" in snap["lines"]
    assert "Step 2/2 : RUN pip install" in snap["lines"]
    assert snap["lines"][-1] == "✓ install completed"
    assert snap["active"] is False
    assert snap["ok"] is True


def test_finish_failure_records_error() -> None:
    buf.start("rt")
    buf.append("rt", "building...")
    buf.finish("rt", ok=False, error="boom")
    snap = buf.snapshot("rt")
    assert snap["ok"] is False
    assert snap["error"] == "boom"
    assert snap["lines"][-1] == "✗ install failed: boom"


def test_start_resets_prior_output() -> None:
    buf.start("rt", header="first")
    buf.append("rt", "old line")
    buf.start("rt", header="second")
    snap = buf.snapshot("rt")
    assert "old line" not in snap["lines"]
    assert snap["lines"] == ["second"]
    assert snap["active"] is True


def test_active_true_while_running() -> None:
    buf.start("rt")
    assert buf.snapshot("rt")["active"] is True


def test_blank_line_runs_are_collapsed() -> None:
    buf.start("rt")
    buf.append("rt", "a\n\n\n\nb")
    lines = buf.snapshot("rt")["lines"]
    # header? start() without header => first line is "a"
    assert lines.count("") <= 1
    assert "a" in lines and "b" in lines


def test_bounded_to_max_lines() -> None:
    buf.start("rt")
    for i in range(buf._MAX_LINES + 500):
        buf.append("rt", f"line {i}")
    snap = buf.snapshot("rt")
    assert len(snap["lines"]) <= buf._MAX_LINES
    # The most recent line survives; the oldest is evicted.
    assert snap["lines"][-1] == f"line {buf._MAX_LINES + 499}"


def test_thread_safe_concurrent_appends() -> None:
    buf.start("rt")

    def worker(n: int) -> None:
        for i in range(200):
            buf.append("rt", f"t{n}-{i}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    snap = buf.snapshot("rt")
    # 4*200 = 800 lines, under the cap — none lost, no crash.
    assert len(snap["lines"]) == 800
