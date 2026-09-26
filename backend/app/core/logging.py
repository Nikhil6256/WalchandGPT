"""Structured logging configuration using structlog."""
import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog for structured JSON logging in production,
    and pretty console output in development."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.APP_ENV == "development":
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]
        renderer = structlog.dev.ConsoleRenderer()
    else:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )
