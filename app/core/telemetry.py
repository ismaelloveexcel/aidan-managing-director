"""
telemetry.py - Lightweight deterministic telemetry logging.

This module intentionally avoids external dependencies and network calls.
It provides a single helper for structured event logging so route handlers
can stay thin while still emitting operational traces.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("aidan.telemetry")


def emit_event(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Emit a structured telemetry event to application logs."""
    envelope = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": payload or {},
    }
    _logger.info("telemetry=%s", json.dumps(envelope, sort_keys=True))

