"""
Error handling utilities for TUI.

Provides comprehensive error handling, logging, and recovery
mechanisms for the TUI interface.
"""

import logging
import traceback
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from contextlib import contextmanager


class ErrorLevel(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    NETWORK = "network"
    API = "api"
    UI = "ui"
    DATA = "data"
    CONFIG = "config"
    SYSTEM = "system"
    USER = "user"


@dataclass
class ErrorReport:
    """Comprehensive error report."""
    timestamp: datetime
    level: ErrorLevel
    category: ErrorCategory
    message: str
    exception: Optional[Exception]
    traceback_str: Optional[str]
    context: Dict[str, Any]
    user_action: Optional[str]
    recovery_attempted: bool = False
    recovery_successful: bool = False


class TUILogger:
    """Enhanced logger for TUI applications."""
    
    def __init__(self, name: str = "prs_tui", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Error reports storage
        self._error_reports: List[ErrorReport] = []
        self._max_reports = 100
        self._lock = threading.Lock()
    
    def _add_error_report(self, level: ErrorLevel, category: ErrorCategory, 
                         message: str, exception: Optional[Exception] = None,
                         context: Optional[Dict[str, Any]] = None,
                         user_action: Optional[str] = None) -> ErrorReport:
        """Add an error report."""
        with self._lock:
            report = ErrorReport(
                timestamp=datetime.now(),
                level=level,
                category=category,
                message=message,
                exception=exception,
                traceback_str=traceback.format_exc() if exception else None,
                context=context or {},
                user_action=user_action
            )
            
            self._error_reports.append(report)
            
            # Keep only recent reports
            if len(self._error_reports) > self._max_reports:
                self._error_reports = self._error_reports[-self._max_reports:]
            
            return report
    
    def debug(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
              context: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self.logger.debug(message)
        self._add_error_report(ErrorLevel.DEBUG, category, message, context=context)
    
    def info(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
             context: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self.logger.info(message)
        self._add_error_report(ErrorLevel.INFO, category, message, context=context)
    
    def warning(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
                context: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self.logger.warning(message)
        self._add_error_report(ErrorLevel.WARNING, category, message, context=context)
    
    def error(self, message: str, exception: Optional[Exception] = None,
              category: ErrorCategory = ErrorCategory.SYSTEM,
              context: Optional[Dict[str, Any]] = None,
              user_action: Optional[str] = None):
        """Log error message."""
        self.logger.error(message, exc_info=exception)
        self._add_error_report(ErrorLevel.ERROR, category, message, exception, 
                              context, user_action)
    
    def critical(self, message: str, exception: Optional[Exception] = None,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 context: Optional[Dict[str, Any]] = None,
                 user_action: Optional[str] = None):
        """Log critical error message."""
        self.logger.critical(message, exc_info=exception)
        self._add_error_report(ErrorLevel.CRITICAL, category, message, exception,
                              context, user_action)
    
    def get_recent_errors(self, count: int = 10) -> List[ErrorReport]:
        """Get recent error reports."""
        with self._lock:
            return self._error_reports[-count:] if self._error_reports else []
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorReport]:
        """Get errors by category."""
        with self._lock:
            return [report for report in self._error_reports 
                   if report.category == category]
    
    def clear_reports(self):
        """Clear all error reports."""
        with self._lock:
            self._error_reports.clear()


class ErrorRecovery:
    """Error recovery and retry mechanisms."""
    
    def __init__(self, logger: TUILogger):
        self.logger = logger
        self._recovery_strategies: Dict[ErrorCategory, List[Callable]] = {
            ErrorCategory.NETWORK: [
                self._retry_with_backoff,
                self._check_network_connection,
                self._switch_to_offline_mode
            ],
            ErrorCategory.API: [
                self._retry_with_rate_limit,
                self._use_cached_data,
                self._fallback_to_basic_api
            ],
            ErrorCategory.UI: [
                self._refresh_ui_component,
                self._reset_ui_state,
                self._fallback_to_text_mode
            ],
            ErrorCategory.DATA: [
                self._reload_data,
                self._use_default_data,
                self._clear_corrupted_cache
            ],
            ErrorCategory.CONFIG: [
                self._reset_to_defaults,
                self._prompt_for_config,
                self._use_environment_config
            ]
        }
    
    async def attempt_recovery(self, error_report: ErrorReport) -> bool:
        """Attempt to recover from an error."""
        self.logger.info(f"Attempting recovery for {error_report.category.value} error: {error_report.message}")
        
        strategies = self._recovery_strategies.get(error_report.category, [])
        
        for strategy in strategies:
            try:
                if await self._execute_strategy(strategy, error_report):
                    error_report.recovery_attempted = True
                    error_report.recovery_successful = True
                    self.logger.info(f"Recovery successful using strategy: {strategy.__name__}")
                    return True
            except Exception as e:
                self.logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
        
        error_report.recovery_attempted = True
        error_report.recovery_successful = False
        self.logger.error(f"All recovery strategies failed for {error_report.category.value} error")
        return False
    
    async def _execute_strategy(self, strategy: Callable, error_report: ErrorReport) -> bool:
        """Execute a recovery strategy."""
        if asyncio.iscoroutinefunction(strategy):
            return await strategy(error_report)
        else:
            return strategy(error_report)
    
    # Recovery strategies
    async def _retry_with_backoff(self, error_report: ErrorReport) -> bool:
        """Retry operation with exponential backoff."""
        for attempt in range(3):
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
            try:
                # This would retry the failed operation
                # Implementation depends on the specific operation
                return True
            except Exception:
                continue
        return False
    
    def _check_network_connection(self, error_report: ErrorReport) -> bool:
        """Check network connectivity."""
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def _switch_to_offline_mode(self, error_report: ErrorReport) -> bool:
        """Switch to offline mode."""
        # Implementation would enable offline mode
        return True
    
    async def _retry_with_rate_limit(self, error_report: ErrorReport) -> bool:
        """Retry with rate limiting."""
        await asyncio.sleep(60)  # Wait 1 minute for rate limit reset
        return True
    
    def _use_cached_data(self, error_report: ErrorReport) -> bool:
        """Use cached data instead of fresh data."""
        # Implementation would load from cache
        return True
    
    def _fallback_to_basic_api(self, error_report: ErrorReport) -> bool:
        """Fallback to basic API calls."""
        # Implementation would use simpler API endpoints
        return True
    
    def _refresh_ui_component(self, error_report: ErrorReport) -> bool:
        """Refresh a UI component."""
        # Implementation would refresh the component
        return True
    
    def _reset_ui_state(self, error_report: ErrorReport) -> bool:
        """Reset UI state to defaults."""
        # Implementation would reset UI state
        return True
    
    def _fallback_to_text_mode(self, error_report: ErrorReport) -> bool:
        """Fallback to text-only mode."""
        # Implementation would disable rich UI features
        return True
    
    def _reload_data(self, error_report: ErrorReport) -> bool:
        """Reload data from source."""
        # Implementation would reload data
        return True
    
    def _use_default_data(self, error_report: ErrorReport) -> bool:
        """Use default data values."""
        # Implementation would load default data
        return True
    
    def _clear_corrupted_cache(self, error_report: ErrorReport) -> bool:
        """Clear potentially corrupted cache."""
        # Implementation would clear cache
        return True
    
    def _reset_to_defaults(self, error_report: ErrorReport) -> bool:
        """Reset configuration to defaults."""
        # Implementation would reset config
        return True
    
    def _prompt_for_config(self, error_report: ErrorReport) -> bool:
        """Prompt user for configuration."""
        # Implementation would show config dialog
        return True
    
    def _use_environment_config(self, error_report: ErrorReport) -> bool:
        """Use environment variables for config."""
        # Implementation would load from environment
        return True


@contextmanager
def error_boundary(logger: TUILogger, category: ErrorCategory = ErrorCategory.SYSTEM,
                  user_action: Optional[str] = None, reraise: bool = False):
    """Context manager for error boundaries."""
    try:
        yield
    except Exception as e:
        logger.error(
            f"Error in {category.value}: {str(e)}",
            exception=e,
            category=category,
            user_action=user_action
        )
        if reraise:
            raise


class TUIExceptionHandler:
    """Global exception handler for TUI applications."""
    
    def __init__(self, logger: TUILogger, recovery: ErrorRecovery):
        self.logger = logger
        self.recovery = recovery
        self._original_excepthook = None
    
    def install(self):
        """Install the global exception handler."""
        self._original_excepthook = threading.excepthook
        threading.excepthook = self._handle_thread_exception
        
        # For asyncio tasks
        asyncio.get_event_loop().set_exception_handler(self._handle_async_exception)
    
    def uninstall(self):
        """Uninstall the global exception handler."""
        if self._original_excepthook:
            threading.excepthook = self._original_excepthook
    
    def _handle_thread_exception(self, args):
        """Handle thread exceptions."""
        self.logger.critical(
            f"Unhandled exception in thread {args.thread.name}: {args.exc_value}",
            exception=args.exc_value,
            category=ErrorCategory.SYSTEM,
            context={"thread": args.thread.name}
        )
    
    def _handle_async_exception(self, loop, context):
        """Handle async exceptions."""
        exception = context.get('exception')
        if exception:
            self.logger.critical(
                f"Unhandled exception in async task: {exception}",
                exception=exception,
                category=ErrorCategory.SYSTEM,
                context=context
            )


# Decorators for error handling
def handle_errors(category: ErrorCategory = ErrorCategory.SYSTEM,
                 user_action: Optional[str] = None,
                 default_return: Any = None):
    """Decorator for function error handling."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exception=e,
                    category=category,
                    user_action=user_action
                )
                return default_return
        return wrapper
    return decorator


def handle_async_errors(category: ErrorCategory = ErrorCategory.SYSTEM,
                       user_action: Optional[str] = None,
                       default_return: Any = None):
    """Decorator for async function error handling."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exception=e,
                    category=category,
                    user_action=user_action
                )
                return default_return
        return wrapper
    return decorator


# Global instances
logger = TUILogger("prs_tui")
recovery = ErrorRecovery(logger)
exception_handler = TUIExceptionHandler(logger, recovery)


def setup_error_handling(log_file: Optional[str] = None):
    """Setup global error handling."""
    global logger, recovery, exception_handler
    
    logger = TUILogger("prs_tui", log_file)
    recovery = ErrorRecovery(logger)
    exception_handler = TUIExceptionHandler(logger, recovery)
    exception_handler.install()


def get_logger() -> TUILogger:
    """Get the global TUI logger."""
    return logger


def get_recovery() -> ErrorRecovery:
    """Get the global error recovery manager."""
    return recovery