"""
Logging utilities for Dify Plugin Daemon.

Provides structured logging with support for JSON and text formats,
trace correlation, and panic/recovery handling.
"""

import logging
import sys
from typing import Optional, Callable, Any
from contextlib import contextmanager

import structlog
from structlog.types import Processor


def setup_logging(
    log_level: str = "info",
    log_format: str = "text",
    log_file: Optional[str] = None,
) -> Optional[Callable[[], None]]:
    """
    Initialize logging configuration.

    Args:
        log_level: Log level (debug, info, warning, error, critical)
        log_format: Output format (text, json)
        log_file: Optional log file path

    Returns:
        Optional close function for log file handler
    """
    # Map string level to logging level
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    level = level_map.get(log_level.lower(), logging.INFO)

    # Configure handlers
    handlers = []
    closer = None

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        handlers.append(file_handler)
        closer = file_handler.close

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # Configure processors based on format
    if log_format == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=processors,
        )
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=processors,
        )

    for handler in handlers:
        handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in handlers:
        root_logger.addHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ] if log_format == "json" else [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return closer


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def recovery_middleware():
    """
    Middleware to recover from panics/exceptions.
    
    In Go, this would catch panics. In Python, we provide exception handling context.
    """
    @contextmanager
    def _recovery_context():
        try:
            yield
        except Exception as e:
            logger = get_logger()
            logger.error("panic recovered", exc_info=e, error=str(e))
            raise
    return _recovery_context()


def trace_middleware():
    """
    Middleware to add trace IDs to log entries.
    
    Integrates with OpenTelemetry for distributed tracing.
    """
    def _add_trace_id(logger: logging.Logger, method_name: str, event_dict: dict) -> dict:
        try:
            from opentelemetry import trace
            current_span = trace.get_current_span()
            if current_span.is_recording():
                trace_id = current_span.get_span_context().trace_id
                span_id = current_span.get_span_context().span_id
                event_dict["trace_id"] = f"{trace_id:032x}"
                event_dict["span_id"] = f"{span_id:016x}"
        except ImportError:
            pass
        return event_dict
    return _add_trace_id


class LoggerMiddleware:
    """ASGI middleware for logging HTTP requests."""

    def __init__(self, app, skip_paths: Optional[list[str]] = None):
        self.app = app
        self.skip_paths = skip_paths or []
        self.logger = get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.skip_paths:
            await self.app(scope, receive, send)
            return

        import time
        start_time = time.time()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                elapsed = time.time() - start_time
                self.logger.info(
                    "http_request",
                    method=scope["method"],
                    path=path,
                    status_code=status_code,
                    duration_ms=elapsed * 1000,
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RecoveryMiddleware:
    """ASGI middleware for recovering from panics."""

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("recovery")

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            self.logger.error("panic recovered", exc_info=e, error=str(e))
            if scope["type"] == "http":
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [[b"content-type", b"application/json"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "internal_server_error", "message": "internal server error"}',
                })
