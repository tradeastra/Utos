"""
Logging configuration for UTOS Trading Engine.

This module sets up structured logging with context and correlation IDs.
"""

import logging
import logging.handlers
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar
import uuid

from core.config import settings


# Context variables for structured logging
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
instance_id: ContextVar[Optional[str]] = ContextVar('instance_id', default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context variables
        if correlation_id.get():
            log_entry['correlation_id'] = correlation_id.get()
        if user_id.get():
            log_entry['user_id'] = user_id.get()
        if instance_id.get():
            log_entry['instance_id'] = instance_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class PlainFormatter(logging.Formatter):
    """Plain text formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text."""
        context_parts = []
        
        if correlation_id.get():
            context_parts.append(f"cid={correlation_id.get()}")
        if user_id.get():
            context_parts.append(f"uid={user_id.get()}")
        if instance_id.get():
            context_parts.append(f"iid={instance_id.get()}")
        
        context_str = f"[{' '.join(context_parts)}] " if context_parts else ""
        
        return (
            f"{datetime.utcnow().isoformat()}Z "
            f"{record.levelname:8} "
            f"{record.name:20} "
            f"{record.funcName}:{record.lineno:3} "
            f"{context_str}"
            f"{record.getMessage()}"
        )


def setup_logging() -> None:
    """Set up logging configuration."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter based on format setting
    if settings.LOG_FORMAT.lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = PlainFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.LOG_FILE:
        # Parse log file size
        size_str = settings.LOG_MAX_SIZE.upper()
        if size_str.endswith('MB'):
            max_bytes = int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            max_bytes = int(size_str[:-2]) * 1024
        else:
            max_bytes = int(size_str)
        
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=max_bytes,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger('redis').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def set_correlation_id(cid: Optional[str] = None) -> None:
    """Set correlation ID for the current context."""
    correlation_id.set(cid or str(uuid.uuid4()))


def set_user_id(uid: Optional[str]) -> None:
    """Set user ID for the current context."""
    user_id.set(uid)


def set_instance_id(iid: Optional[str]) -> None:
    """Set instance ID for the current context."""
    instance_id.set(iid)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return correlation_id.get()


def get_user_id() -> Optional[str]:
    """Get user ID from current context."""
    return user_id.get()


def get_instance_id() -> Optional[str]:
    """Get instance ID from current context."""
    return instance_id.get()


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + '.' + self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys())
            }
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(
                f"Function {func.__name__} failed",
                extra={'error': str(e), 'error_type': type(e).__name__}
            )
            raise
    
    return wrapper


def log_performance(func):
    """Decorator to log function performance."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = datetime.utcnow()
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(
                f"Performance: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
            )
            
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.error(
                f"Performance: {func.__name__} failed",
                extra={
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            raise
    
    return wrapper


# Initialize logging
setup_logging()


# Export logger functions
__all__ = [
    'get_logger',
    'set_correlation_id',
    'set_user_id',
    'set_instance_id',
    'get_correlation_id',
    'get_user_id',
    'get_instance_id',
    'LoggerMixin',
    'log_function_call',
    'log_performance',
]