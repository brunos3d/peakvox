from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


RuntimeOperationType = Literal["install", "update", "start", "stop", "remove", "build"]
RuntimeOperationStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


@dataclass(frozen=True)
class RuntimeOperation:
    id: str
    runtime_id: str
    type: RuntimeOperationType
    status: RuntimeOperationStatus
    progress: int
    message: str
    started_at: datetime
    updated_at: datetime
    cancellable: bool
    error: Optional[str] = None


class RuntimeOperationConflict(RuntimeError):
    """Raised when another operation is already in progress for a runtime."""


class RuntimeOperationNotFound(RuntimeError):
    """Raised when a requested operation cannot be found."""
