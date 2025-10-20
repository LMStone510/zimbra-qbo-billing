# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Parser for Zimbra weekly usage reports.

Handles parsing of the weekly report format to extract:
- Domain names
- Class of Service (CoS) names and account counts
- Report dates
- Quota sizes from CoS names
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ZimbraReportParser:
    """Parser for Zimbra usage reports."""

    def __init__(self):
        """Initialize the parser."""
        # Pattern to extract quota size from CoS name (e.g., 'customer-50gb' -> 50)
        self.quota_pattern = re.compile(r'(\d+)\s*gb', re.IGNORECASE)

        # Pattern to extract date from report filename or header
        self.date_pattern = re.compile(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})')

    def parse_report(self, report_text: str, report_date: Optional[datetime] = None) -> List[Dict]:
        """Parse a Zimbra weekly usage report.

        Expected format:
        domain.com
            cos-name-1: 10
            cos-name-2: 5

        another-domain.com
            cos-name-1: 3

        Args:
            report_text: Text content of the report
            report_date: Date of the report (if known)

        Returns:
            List of dictionaries with structure:
            [
                {
                    'domain': 'example.com',
                    'cos_usage': {
                        'customer-50gb': 10,
                        'customer-20gb': 5
                    },
                    'report_date': datetime object
                },
                ...
            ]
        """
        if not report_text or not report_text.strip():
            logger.warning("Empty report text provided")
            return []

        results = []
        current_domain = None
        current_cos_usage = {}

        lines = report_text.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()

            # Skip empty lines and separator lines
            if not line.strip() or line.strip().startswith('---'):
                continue

            # Check for domain header line: "| CoS Usage for domain.com:"
            if line.strip().startswith('| CoS Usage for '):
                # Save previous domain if exists
                if current_domain and current_cos_usage:
                    results.append({
                        'domain': current_domain,
                        'cos_usage': current_cos_usage.copy(),
                        'report_date': report_date
                    })
                    current_cos_usage = {}

                # Extract domain from line: "| CoS Usage for domain.com:"
                match = re.search(r'\| CoS Usage for (.+?):', line)
                if match:
                    domain = match.group(1).strip()
                    if self._is_valid_domain(domain):
                        current_domain = domain
                        logger.debug(f"Line {line_num}: Found domain: {domain}")
                    else:
                        logger.debug(f"Line {line_num}: Invalid domain: {domain}")
                        current_domain = None
                continue

            # Check for CoS line: "- cos-name: count"
            if line.strip().startswith('- ') and current_domain:
                cos_data = self._parse_cos_line(line)
                if cos_data:
                    cos_name, count = cos_data
                    current_cos_usage[cos_name] = count
                    logger.debug(f"Line {line_num}: Added {cos_name}: {count} for {current_domain}")
                else:
                    logger.debug(f"Line {line_num}: Could not parse CoS line: {line}")

        # Don't forget the last domain
        if current_domain and current_cos_usage:
            results.append({
                'domain': current_domain,
                'cos_usage': current_cos_usage.copy(),
                'report_date': report_date
            })

        logger.info(f"Parsed {len(results)} domains from report")
        return results

    def _parse_cos_line(self, line: str) -> Optional[Tuple[str, int]]:
        """Parse a CoS line to extract name and count.

        Expected formats:
        - "- cos-name: 10" (with leading dash)
        - "    cos-name: 10" (with leading spaces)

        Args:
            line: CoS line from report

        Returns:
            Tuple of (cos_name, count) or None if parsing fails
        """
        # Remove leading whitespace and dash
        line = line.strip()
        if line.startswith('- '):
            line = line[2:].strip()

        # Split on colon
        parts = line.split(':', 1)
        if len(parts) != 2:
            return None

        cos_name = parts[0].strip()
        count_str = parts[1].strip()

        try:
            count = int(count_str)
            return (cos_name, count)
        except ValueError:
            logger.warning(f"Could not parse count from CoS line: {line}")
            return None

    def _is_valid_domain(self, domain: str) -> bool:
        """Check if a string looks like a valid domain name.

        Args:
            domain: Potential domain name

        Returns:
            True if it looks like a domain
        """
        if not domain:
            return False

        # Basic checks
        if len(domain) > 253:
            return False

        # Must contain at least one dot
        if '.' not in domain:
            return False

        # Must not contain spaces
        if ' ' in domain:
            return False

        # Simple regex check for domain format
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        )

        return bool(domain_pattern.match(domain))

    def extract_quota_from_cos(self, cos_name: str) -> Optional[int]:
        """Extract quota size in GB from CoS name.

        Examples:
            'customer-50gb' -> 50
            'customer-20GB' -> 20
            'archive-100gb' -> 100

        Args:
            cos_name: Class of Service name

        Returns:
            Quota in GB or None if not found
        """
        match = self.quota_pattern.search(cos_name)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from report filename.

        Examples:
            'report_2025-10-14.txt' -> datetime(2025, 10, 14)
            'usage_20251014.txt' -> datetime(2025, 10, 14)

        Args:
            filename: Report filename

        Returns:
            Datetime object or None
        """
        match = self.date_pattern.search(filename)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            except (ValueError, IndexError):
                logger.warning(f"Could not parse date from filename: {filename}")
        return None

    def parse_report_file(self, filepath: str) -> List[Dict]:
        """Parse a report from a file.

        Args:
            filepath: Path to report file

        Returns:
            Parsed report data
        """
        import os

        # Try to extract date from filename
        filename = os.path.basename(filepath)
        report_date = self.extract_date_from_filename(filename)

        # Read and parse file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                report_text = f.read()
            return self.parse_report(report_text, report_date)
        except Exception as e:
            logger.error(f"Error reading report file {filepath}: {e}")
            raise

    def validate_parsed_data(self, parsed_data: List[Dict]) -> bool:
        """Validate parsed report data structure.

        Args:
            parsed_data: Parsed report data

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(parsed_data, list):
            logger.error("Parsed data must be a list")
            return False

        for i, record in enumerate(parsed_data):
            if not isinstance(record, dict):
                logger.error(f"Record {i} is not a dictionary")
                return False

            if 'domain' not in record:
                logger.error(f"Record {i} missing 'domain' field")
                return False

            if 'cos_usage' not in record:
                logger.error(f"Record {i} missing 'cos_usage' field")
                return False

            if not isinstance(record['cos_usage'], dict):
                logger.error(f"Record {i} 'cos_usage' is not a dictionary")
                return False

            # Validate CoS usage counts
            for cos_name, count in record['cos_usage'].items():
                if not isinstance(count, int) or count < 0:
                    logger.error(f"Record {i}: Invalid count for CoS {cos_name}: {count}")
                    return False

        return True


def parse_zimbra_report(report_text: str, report_date: Optional[datetime] = None) -> List[Dict]:
    """Convenience function to parse a Zimbra report.

    Args:
        report_text: Text content of the report
        report_date: Optional date of the report

    Returns:
        List of parsed domain/CoS usage data
    """
    parser = ZimbraReportParser()
    return parser.parse_report(report_text, report_date)
