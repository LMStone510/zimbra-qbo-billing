"""Tests for Zimbra report parser."""

import unittest
from datetime import datetime

from src.zimbra.parser import ZimbraReportParser


class TestZimbraReportParser(unittest.TestCase):
    """Test cases for ZimbraReportParser."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = ZimbraReportParser()

    def test_parse_simple_report(self):
        """Test parsing a simple report."""
        report_text = """example.com
    customer-50gb: 10
    customer-20gb: 5

another-example.com
    customer-50gb: 3
"""
        report_date = datetime(2025, 10, 14)
        results = self.parser.parse_report(report_text, report_date)

        self.assertEqual(len(results), 2)

        # Check first domain
        self.assertEqual(results[0]['domain'], 'example.com')
        self.assertEqual(results[0]['cos_usage']['customer-50gb'], 10)
        self.assertEqual(results[0]['cos_usage']['customer-20gb'], 5)
        self.assertEqual(results[0]['report_date'], report_date)

        # Check second domain
        self.assertEqual(results[1]['domain'], 'another-example.com')
        self.assertEqual(results[1]['cos_usage']['customer-50gb'], 3)

    def test_parse_empty_report(self):
        """Test parsing an empty report."""
        results = self.parser.parse_report("")
        self.assertEqual(len(results), 0)

    def test_extract_quota_from_cos(self):
        """Test extracting quota from CoS name."""
        self.assertEqual(self.parser.extract_quota_from_cos('customer-50gb'), 50)
        self.assertEqual(self.parser.extract_quota_from_cos('customer-20GB'), 20)
        self.assertEqual(self.parser.extract_quota_from_cos('customer-100gb'), 100)
        self.assertIsNone(self.parser.extract_quota_from_cos('customer-basic'))

    def test_validate_domain(self):
        """Test domain validation."""
        self.assertTrue(self.parser._is_valid_domain('example.com'))
        self.assertTrue(self.parser._is_valid_domain('mail.example.com'))
        self.assertTrue(self.parser._is_valid_domain('sub.domain.example.co.uk'))

        self.assertFalse(self.parser._is_valid_domain('invalid'))
        self.assertFalse(self.parser._is_valid_domain('has spaces.com'))
        self.assertFalse(self.parser._is_valid_domain(''))


if __name__ == '__main__':
    unittest.main()
