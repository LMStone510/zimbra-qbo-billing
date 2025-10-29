"""Tests for QuickBooks query string escaping.

Verifies that special characters are properly escaped in QBO queries.
"""

import unittest
import sys
import os

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qbo.client import _escape_qbo_query_string


class TestQueryEscaping(unittest.TestCase):
    """Test QBO query string escaping."""

    def test_escape_single_quotes(self):
        """Test that single quotes are escaped."""
        input_str = "O'Brien Company"

        result = _escape_qbo_query_string(input_str)

        self.assertEqual(result, "O''Brien Company")

    def test_escape_percent_wildcard(self):
        """Test that % wildcard is escaped."""
        input_str = "100% Complete"

        result = _escape_qbo_query_string(input_str)

        self.assertEqual(result, "100\\% Complete")

    def test_escape_underscore_wildcard(self):
        """Test that _ wildcard is escaped."""
        input_str = "test_user"

        result = _escape_qbo_query_string(input_str)

        self.assertEqual(result, "test\\_user")

    def test_escape_combined_special_chars(self):
        """Test escaping multiple special characters."""
        input_str = "O'Brien's 50% _complete"

        result = _escape_qbo_query_string(input_str)

        self.assertEqual(result, "O''Brien''s 50\\% \\_complete")

    def test_length_limit(self):
        """Test that excessively long strings are truncated."""
        long_str = "A" * 300

        result = _escape_qbo_query_string(long_str)

        self.assertEqual(len(result), 255)

    def test_empty_string(self):
        """Test handling of empty string."""
        result = _escape_qbo_query_string("")

        self.assertEqual(result, "")

    def test_none_value(self):
        """Test handling of None value."""
        result = _escape_qbo_query_string(None)

        self.assertIsNone(result)

    def test_normal_string_unchanged(self):
        """Test that normal strings pass through unchanged."""
        input_str = "Regular Company Name"

        result = _escape_qbo_query_string(input_str)

        self.assertEqual(result, "Regular Company Name")


if __name__ == '__main__':
    unittest.main()
