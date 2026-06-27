from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.logging import get_logger, get_request_id


def log_event(
    logger_name: str,
    event: str,
    *,
    level: str = "info",
    **fields: Any,
) -> None:
    """Emit a structured log line as JSON (stdlib logging compatible)."""
    logger = get_logger(logger_name)
    payload = {
        "event": event,
        "request_id": get_request_id(),
        **{k: v for k, v in fields.items() if v is not None},
    }
    message = json.dumps(payload, default=str)
    getattr(logger, level, logger.info)(message)


@contextmanager
def log_timing(
    logger_name: str,
    event: str,
    **fields: Any,
) -> Iterator[None]:
    """Log start/end of an operation with execution_time_ms."""
    start = time.perf_counter()
    log_event(logger_name, f"{event}_start", **fields)
    try:
        yield
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(
            logger_name,
            f"{event}_failed",
            level="error",
            execution_time_ms=elapsed_ms,
            error=str(exc),
            **fields,
        )
        raise
    else:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(
            logger_name,
            f"{event}_end",
            execution_time_ms=elapsed_ms,
            **fields,
        )
