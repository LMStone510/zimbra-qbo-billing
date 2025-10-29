# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""QuickBooks API error taxonomy and retry logic.

Provides structured error handling with classification of errors as:
- Transient (429, 5xx) - should be retried
- Permanent (4xx) - should not be retried
- Auth errors - require token refresh
"""

import logging
import time
import random
from typing import Optional, Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QBOError(Exception):
    """Base exception for QuickBooks API errors."""

    def __init__(self, message: str, operation: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        """Initialize QBO error.

        Args:
            message: Error message
            operation: Operation that failed
            original_error: Original exception if wrapped
        """
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.original_error = original_error

    def is_retryable(self) -> bool:
        """Check if this error should be retried.

        Returns:
            True if error is transient and should be retried
        """
        return False


class QBORateLimitError(QBOError):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        """Initialize rate limit error.

        Args:
            retry_after: Seconds to wait before retry
            **kwargs: Additional error args
        """
        super().__init__("QuickBooks API rate limit exceeded", **kwargs)
        self.retry_after = retry_after or 60

    def is_retryable(self) -> bool:
        return True


class QBOAuthError(QBOError):
    """Authentication/authorization error (401, 403)."""

    def __init__(self, **kwargs):
        super().__init__("QuickBooks authentication failed", **kwargs)

    def is_retryable(self) -> bool:
        # Auth errors need token refresh, not simple retry
        return False


class QBOValidationError(QBOError):
    """Validation error (400)."""

    def __init__(self, validation_errors: Optional[list] = None, **kwargs):
        """Initialize validation error.

        Args:
            validation_errors: List of validation error details
            **kwargs: Additional error args
        """
        super().__init__("QuickBooks validation error", **kwargs)
        self.validation_errors = validation_errors or []

    def is_retryable(self) -> bool:
        return False


class QBONotFoundError(QBOError):
    """Resource not found (404)."""

    def __init__(self, resource_type: Optional[str] = None,
                 resource_id: Optional[str] = None, **kwargs):
        """Initialize not found error.

        Args:
            resource_type: Type of resource (Customer, Invoice, etc.)
            resource_id: ID of missing resource
            **kwargs: Additional error args
        """
        message = f"QuickBooks resource not found"
        if resource_type:
            message += f": {resource_type}"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id

    def is_retryable(self) -> bool:
        return False


class QBOServerError(QBOError):
    """Server error (5xx)."""

    def __init__(self, status_code: Optional[int] = None, **kwargs):
        """Initialize server error.

        Args:
            status_code: HTTP status code
            **kwargs: Additional error args
        """
        super().__init__(f"QuickBooks server error (status: {status_code})", **kwargs)
        self.status_code = status_code

    def is_retryable(self) -> bool:
        return True


class QBONetworkError(QBOError):
    """Network/connection error."""

    def __init__(self, **kwargs):
        super().__init__("Network error communicating with QuickBooks", **kwargs)

    def is_retryable(self) -> bool:
        return True


def classify_qbo_error(error: Exception, operation: Optional[str] = None) -> QBOError:
    """Classify an exception into appropriate QBO error type.

    Args:
        error: Exception to classify
        operation: Operation that failed

    Returns:
        Classified QBOError subclass
    """
    error_str = str(error).lower()

    # Check for rate limiting
    if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
        return QBORateLimitError(operation=operation, original_error=error)

    # Check for auth errors
    if '401' in error_str or '403' in error_str or 'unauthorized' in error_str or 'forbidden' in error_str:
        return QBOAuthError(operation=operation, original_error=error)

    # Check for validation errors
    if '400' in error_str or 'validation' in error_str or 'invalid' in error_str:
        return QBOValidationError(operation=operation, original_error=error)

    # Check for not found
    if '404' in error_str or 'not found' in error_str:
        return QBONotFoundError(operation=operation, original_error=error)

    # Check for server errors (5xx)
    if any(code in error_str for code in ['500', '502', '503', '504']):
        status_code = None
        for code in ['500', '502', '503', '504']:
            if code in error_str:
                status_code = int(code)
                break
        return QBOServerError(status_code=status_code, operation=operation, original_error=error)

    # Check for network errors
    if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'unreachable']):
        return QBONetworkError(operation=operation, original_error=error)

    # Default to generic QBO error
    return QBOError(str(error), operation=operation, original_error=error)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    # Classify the error
                    operation = func.__name__
                    qbo_error = classify_qbo_error(e, operation=operation)
                    last_error = qbo_error

                    # Don't retry if error is not retryable
                    if not qbo_error.is_retryable():
                        logger.error(f"{operation}: Non-retryable error: {qbo_error}")
                        raise qbo_error

                    # Check if we've exhausted retries
                    if attempt >= max_retries:
                        logger.error(f"{operation}: Max retries ({max_retries}) exceeded")
                        raise qbo_error

                    # Calculate delay with exponential backoff
                    if isinstance(qbo_error, QBORateLimitError):
                        # Use server-provided retry-after if available
                        delay = qbo_error.retry_after
                    else:
                        delay = min(initial_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"{operation}: Attempt {attempt + 1}/{max_retries} failed "
                        f"with {type(qbo_error).__name__}. Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_error:
                raise last_error
            raise QBOError(f"Unexpected error in retry logic for {func.__name__}")

        return wrapper
    return decorator
