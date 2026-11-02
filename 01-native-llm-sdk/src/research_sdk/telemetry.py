"""Allowlisted JSON events: never record questions, text, tokens, or tool arguments."""

import json
import logging
from contextvars import ContextVar

trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
logger = logging.getLogger("researchops.trace")
ALLOWED = {
    "run_id",
    "action_id",
    "request_id",
    "outcome",
    "duration_ms",
    "count",
    "mode",
    "stage",
    "rounds",
    "tool_calls",
    "usage_tokens",
    "status_code",
    "version",
}


def emit(event: str, **fields) -> dict:
    record = {
        "event": event,
        "trace_id": trace_id.get(),
        **{key: value for key, value in fields.items() if key in ALLOWED},
    }
    logger.info(json.dumps(record, separators=(",", ":")))
    return record
