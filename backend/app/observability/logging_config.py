"""Structured JSON logging configuration with PII and secret redaction."""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re
import sys
from typing import Any, Dict, Optional

# Context variable holding the current active request ID
current_request_id: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)

# Regular expressions for identifying sensitive patterns to redact
SENSITIVE_PATTERNS = [
    (re.compile(r"(api[-_]?key|secret[-_]?key|password|token|admin_key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{6,})['\"]?", re.IGNORECASE), r"\1=[REDACTED]"),
    (re.compile(r"bearer\s+([a-zA-Z0-9_\-\.]{10,})", re.IGNORECASE), r"Bearer [REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), r"[REDACTED_EMAIL]"),
    (re.compile(r"\b(\+?91[\s\-]?)?[6789]\d{9}\b"), r"[REDACTED_PHONE]"),
]


def redact_sensitive_text(text: str) -> str:
    """Scrub secrets, passwords, emails, and phone numbers from log output."""
    if not isinstance(text, str):
        return text
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter outputting clean, machine-parsable JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = current_request_id.get() or getattr(record, "request_id", None)

        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_text(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if req_id:
            log_data["request_id"] = req_id

        # Attach extra structured fields if present
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName", "request_id"
            }:
                if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                    if isinstance(val, str):
                        log_data[key] = redact_sensitive_text(val)
                    else:
                        log_data[key] = val

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """Initialize application root and component loggers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
        )

    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.ERROR)
