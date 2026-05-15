from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Final

_request_id_ctx: Final[ContextVar[str | None]] = ContextVar(
    "request_id", default=None
)

_CONFIGURED: bool = False
_LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
_LOG_BACKUP_COUNT: int = 5


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def set_request_id(value: str | None) -> None:
    _request_id_ctx.set(value)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get() or "-"  # type: ignore[attr-defined]
        return True


def setup_logging(level_name: str = "INFO", logs_dir: str = "logs") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, level_name.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    req_filter = _RequestIdFilter()
    fmt = (
        "%(asctime)s | %(levelname)s | %(name)s | "
        "req=%(request_id)s | %(message)s"
    )
    datefmt = "%Y-%m-%dT%H:%M:%S%z"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    console.addFilter(req_filter)
    root.addHandler(console)

    try:
        os.makedirs(logs_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, "m360.log"),
            maxBytes=_LOG_FILE_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(req_filter)
        root.addHandler(file_handler)
    except (OSError, PermissionError):
        root.warning("Skipping file logging — cannot write to %s", logs_dir)

    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    base = "m360"
    return logging.getLogger(base if not name else f"{base}.{name}")
