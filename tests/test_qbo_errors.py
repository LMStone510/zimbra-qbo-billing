"""Tests for QuickBooks error taxonomy and classification.

Verifies that errors are properly classified and retry logic works correctly.
"""

import unittest
from src.qbo.errors import (
    QBOError, QBORateLimitError, QBOAuthError, QBOValidationError,
    QBONotFoundError, QBOServerError, QBONetworkError,
    classify_qbo_error
)


class TestQBOErrorClassification(unittest.TestCase):
    """Test error classification logic."""

    def test_classify_rate_limit_error(self):
        """Test classification of rate limit errors."""
        error = Exception("429 Too Many Requests")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBORateLimitError)
        self.assertTrue(classified.is_retryable())

    def test_classify_auth_error(self):
        """Test classification of auth errors."""
        error = Exception("401 Unauthorized")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBOAuthError)
        self.assertFalse(classified.is_retryable())

    def test_classify_validation_error(self):
        """Test classification of validation errors."""
        error = Exception("400 Bad Request - Invalid field value")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBOValidationError)
        self.assertFalse(classified.is_retryable())

    def test_classify_not_found_error(self):
        """Test classification of not found errors."""
        error = Exception("404 Not Found")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBONotFoundError)
        self.assertFalse(classified.is_retryable())

    def test_classify_server_error(self):
        """Test classification of server errors."""
        error = Exception("500 Internal Server Error")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBOServerError)
        self.assertTrue(classified.is_retryable())

    def test_classify_network_error(self):
        """Test classification of network errors."""
        error = Exception("Connection timeout")

        classified = classify_qbo_error(error, operation="test")

        self.assertIsInstance(classified, QBONetworkError)
        self.assertTrue(classified.is_retryable())

    def test_retryable_errors(self):
        """Test that transient errors are marked retryable."""
        retryable_errors = [
            QBORateLimitError(),
            QBOServerError(),
            QBONetworkError(),
        ]

        for error in retryable_errors:
            self.assertTrue(error.is_retryable(),
                          f"{type(error).__name__} should be retryable")

    def test_non_retryable_errors(self):
        """Test that permanent errors are not retryable."""
        non_retryable_errors = [
            QBOAuthError(),
            QBOValidationError(),
            QBONotFoundError(),
        ]

        for error in non_retryable_errors:
            self.assertFalse(error.is_retryable(),
                           f"{type(error).__name__} should not be retryable")


class TestQBOErrorAttributes(unittest.TestCase):
    """Test error attribute storage."""

    def test_error_stores_operation(self):
        """Test that errors store the operation name."""
        error = QBOError("Test error", operation="create_invoice")

        self.assertEqual(error.operation, "create_invoice")

    def test_error_stores_original_exception(self):
        """Test that errors store the original exception."""
        original = ValueError("Original error")
        error = QBOError("Wrapped", original_error=original)

        self.assertEqual(error.original_error, original)

    def test_rate_limit_stores_retry_after(self):
        """Test that rate limit errors store retry-after value."""
        error = QBORateLimitError(retry_after=120)

        self.assertEqual(error.retry_after, 120)

    def test_not_found_stores_resource_info(self):
        """Test that not found errors store resource information."""
        error = QBONotFoundError(
            resource_type="Customer",
            resource_id="123"
        )

        self.assertEqual(error.resource_type, "Customer")
        self.assertEqual(error.resource_id, "123")


if __name__ == '__main__':
    unittest.main()
