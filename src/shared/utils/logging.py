"""Logging utilities for consistent error handling."""

import logging
import traceback
from typing import Any, Optional
from functools import wraps


def get_logger(name: str) -> logging.Logger:
    """Get a logger with consistent configuration."""
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """Log exception with consistent format."""
    logger.error(f"{message}: {exc}", exc_info=True)


def safe_execute(logger: logging.Logger, operation_name: str):
    """Decorator for safe execution with logging."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_exception(logger, f"Error in {operation_name}", e)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_exception(logger, f"Error in {operation_name}", e)
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x0080 else sync_wrapper
    return decorator


class StructuredLogger:
    """Structured logger for consistent application logging."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        if kwargs:
            self.logger.info(f"{message} | {kwargs}")
        else:
            self.logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        if kwargs:
            self.logger.warning(f"{message} | {kwargs}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """Log error message with structured data."""
        if kwargs:
            message = f"{message} | {kwargs}"
        
        if exc:
            self.logger.error(message, exc_info=exc)
        else:
            self.logger.error(message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        if kwargs:
            self.logger.debug(f"{message} | {kwargs}")
        else:
            self.logger.debug(message)