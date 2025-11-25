"""Logging utilities for Travel Assistant API.

This module provides structured JSON logging for:
- API requests and responses
- Model latency metrics
- Error events with stack traces
- Request ID correlation
"""

import logging
import json
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable to store request ID across async calls
request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log entry
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data, default=str)


def setup_logger(
    name: str = "travel_assistant_api",
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_file: str = "app.log",
) -> logging.Logger:
    """Set up a logger with JSON formatting.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_to_file: Whether to log to file (default: False)
        log_file: Log file path if log_to_file is True

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # Optional file handler
    if log_to_file:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,  # 10MB
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get or create the global logger instance.

    Returns:
        logging.Logger: Logger instance
    """
    global _logger
    if _logger is None:
        from pathlib import Path

        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)  # Set up logger with file logging enabled
        log_file = log_dir / "travel_assistant.log"
        _logger = setup_logger(
            name="travel_assistant_api", log_to_file=True, log_file=str(log_file)
        )
    return _logger


def generate_request_id() -> str:
    """Generate a unique request ID.

    Returns:
        str: UUID-based request ID
    """
    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    """Set the request ID in the context.

    Args:
        request_id: Request ID to set
    """
    request_id_context.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context.

    Returns:
        Optional[str]: Current request ID or None
    """
    return request_id_context.get()


def log_request(
    endpoint: str,
    method: str,
    request_data: Dict[str, Any],
    request_id: Optional[str] = None,
) -> str:
    """Log an incoming API request.

    Args:
        endpoint: API endpoint path
        method: HTTP method
        request_data: Request payload
        request_id: Optional request ID (generated if not provided)

    Returns:
        str: Request ID for correlation
    """
    if request_id is None:
        request_id = generate_request_id()

    set_request_id(request_id)

    logger = get_logger()
    logger.info(
        f"Incoming request: {method} {endpoint}",
        extra={
            "extra": {
                "event_type": "api_request",
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "request_data": request_data,
            }
        },
    )

    return request_id


def log_response(
    endpoint: str,
    status_code: int,
    latency_ms: int,
    response_size: int = 0,
    request_id: Optional[str] = None,
) -> None:
    """Log an API response.

    Args:
        endpoint: API endpoint path
        status_code: HTTP status code
        latency_ms: Request latency in milliseconds
        response_size: Response size in bytes
        request_id: Request ID for correlation
    """
    if request_id is None:
        request_id = get_request_id()

    logger = get_logger()
    logger.info(
        f"Response sent: {status_code} {endpoint}",
        extra={
            "extra": {
                "event_type": "api_response",
                "request_id": request_id,
                "endpoint": endpoint,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "response_size_bytes": response_size,
            }
        },
    )


def log_model_latency(
    model_name: str, latency_ms: int, request_id: Optional[str] = None
) -> None:
    """Log model response latency.

    Args:
        model_name: Name of the model (flash or pro)
        latency_ms: Model response time in milliseconds
        request_id: Request ID for correlation
    """
    if request_id is None:
        request_id = get_request_id()

    logger = get_logger()
    logger.info(
        f"Model latency: {model_name}",
        extra={
            "extra": {
                "event_type": "model_latency",
                "request_id": request_id,
                "model_name": model_name,
                "latency_ms": latency_ms,
            }
        },
    )


def log_error(
    error: Exception,
    context: str = "",
    additional_data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> None:
    """Log an error with full stack trace.

    Args:
        error: Exception that occurred
        context: Context where error occurred
        additional_data: Additional contextual data
        request_id: Request ID for correlation
    """
    if request_id is None:
        request_id = get_request_id()

    logger = get_logger()

    extra_data = {
        "event_type": "error",
        "request_id": request_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
    }

    if additional_data:
        extra_data.update(additional_data)

    logger.error(
        f"Error in {context}: {str(error)}", exc_info=True, extra={"extra": extra_data}
    )


def log_info(message: str, **kwargs: Any) -> None:
    """Log an info message with optional extra data.

    Args:
        message: Log message
        **kwargs: Additional key-value pairs to log
    """
    logger = get_logger()
    extra_data = {"event_type": "info", "request_id": get_request_id()}
    extra_data.update(kwargs)
    logger.info(message, extra={"extra": extra_data})


def log_debug(message: str, **kwargs: Any) -> None:
    """Log a debug message with optional extra data.

    Args:
        message: Log message
        **kwargs: Additional key-value pairs to log
    """
    logger = get_logger()
    extra_data = {"event_type": "debug", "request_id": get_request_id()}
    extra_data.update(kwargs)
    logger.debug(message, extra={"extra": extra_data})
