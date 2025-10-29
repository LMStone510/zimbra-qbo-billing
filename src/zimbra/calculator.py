# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""High-water mark calculator for Zimbra usage data.

Processes weekly reports to calculate monthly maximum usage per domain/CoS.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class HighwaterCalculator:
    """Calculates monthly high-water marks from weekly usage data."""

    def calculate_monthly_highwater(self, parsed_reports: List[Dict]) -> Dict[Tuple[str, str], Dict]:
        """Calculate high-water marks from multiple weekly reports.

        Takes parsed report data and finds the maximum usage count for each
        domain/CoS combination across all reports in a month.

        Args:
            parsed_reports: List of parsed report data from parser
                           Each item is a dict with 'domain', 'cos_usage', 'report_date'

        Returns:
            Dictionary mapping (domain, cos) -> {'count': max_count, 'dates': [dates_seen]}
            Example:
            {
                ('example.com', 'customer-50gb'): {
                    'count': 15,
                    'dates': [datetime(...), datetime(...)]
                }
            }
        """
        if not parsed_reports:
            logger.warning("No reports provided for highwater calculation")
            return {}

        # Dictionary to track maximum counts and when they were seen
        highwater_data = defaultdict(lambda: {'count': 0, 'dates': []})

        # Process each report
        for report in parsed_reports:
            domain = report.get('domain')
            cos_usage = report.get('cos_usage', {})
            report_date = report.get('report_date')

            if not domain:
                logger.warning("Report entry missing domain, skipping")
                continue

            # Process each CoS for this domain
            for cos_name, count in cos_usage.items():
                key = (domain, cos_name)

                # Track the date this count was seen
                highwater_data[key]['dates'].append(report_date)

                # Update maximum if this is higher
                if count > highwater_data[key]['count']:
                    highwater_data[key]['count'] = count
                    highwater_data[key]['peak_date'] = report_date

        logger.info(f"Calculated highwater marks for {len(highwater_data)} domain/CoS combinations")

        return dict(highwater_data)

    def aggregate_by_domain(self, highwater_data: Dict[Tuple[str, str], Dict]) -> Dict[str, Dict[str, int]]:
        """Aggregate highwater data by domain.

        Args:
            highwater_data: Output from calculate_monthly_highwater()

        Returns:
            Dictionary mapping domain -> {cos_name: count}
            Example:
            {
                'example.com': {
                    'customer-50gb': 15,
                    'customer-20gb': 8
                }
            }
        """
        result = defaultdict(dict)

        for (domain, cos_name), data in highwater_data.items():
            result[domain][cos_name] = data['count']

        return dict(result)

    def aggregate_by_cos(self, highwater_data: Dict[Tuple[str, str], Dict]) -> Dict[str, int]:
        """Aggregate highwater data by CoS (sum across all domains).

        Args:
            highwater_data: Output from calculate_monthly_highwater()

        Returns:
            Dictionary mapping cos_name -> total_count
            Example:
            {
                'customer-50gb': 150,
                'customer-20gb': 85
            }
        """
        result = defaultdict(int)

        for (domain, cos_name), data in highwater_data.items():
            result[cos_name] += data['count']

        return dict(result)

    def get_summary_stats(self, highwater_data: Dict[Tuple[str, str], Dict]) -> Dict:
        """Get summary statistics for highwater data.

        Args:
            highwater_data: Output from calculate_monthly_highwater()

        Returns:
            Dictionary with summary statistics
        """
        if not highwater_data:
            return {
                'total_domains': 0,
                'total_cos_types': 0,
                'total_accounts': 0,
                'domain_count': 0,
            }

        domains = set()
        cos_types = set()
        total_accounts = 0

        for (domain, cos_name), data in highwater_data.items():
            domains.add(domain)
            cos_types.add(cos_name)
            total_accounts += data['count']

        return {
            'total_domains': len(domains),
            'total_cos_types': len(cos_types),
            'total_accounts': total_accounts,
            'domain_cos_combinations': len(highwater_data),
        }

    def compare_with_previous_month(self, current_highwater: Dict[Tuple[str, str], Dict],
                                   previous_highwater: Dict[Tuple[str, str], Dict]) -> Dict:
        """Compare current month's highwater with previous month.

        Args:
            current_highwater: Current month's highwater data
            previous_highwater: Previous month's highwater data

        Returns:
            Dictionary with comparison data:
            {
                'new': [(domain, cos, count), ...],  # New domain/CoS combinations
                'removed': [(domain, cos), ...],      # Removed combinations
                'increased': [(domain, cos, old, new), ...],
                'decreased': [(domain, cos, old, new), ...],
                'unchanged': [(domain, cos, count), ...]
            }
        """
        result = {
            'new': [],
            'removed': [],
            'increased': [],
            'decreased': [],
            'unchanged': []
        }

        # Find new and changed combinations
        for key, current_data in current_highwater.items():
            domain, cos = key
            current_count = current_data['count']

            if key not in previous_highwater:
                result['new'].append((domain, cos, current_count))
            else:
                previous_count = previous_highwater[key]['count']
                if current_count > previous_count:
                    result['increased'].append((domain, cos, previous_count, current_count))
                elif current_count < previous_count:
                    result['decreased'].append((domain, cos, previous_count, current_count))
                else:
                    result['unchanged'].append((domain, cos, current_count))

        # Find removed combinations
        for key in previous_highwater:
            if key not in current_highwater:
                domain, cos = key
                result['removed'].append((domain, cos))

        return result

    def filter_by_domain_pattern(self, highwater_data: Dict[Tuple[str, str], Dict],
                                 patterns: List[str]) -> Dict[Tuple[str, str], Dict]:
        """Filter highwater data by domain patterns (for exclusions).

        Args:
            highwater_data: Highwater data to filter
            patterns: List of fnmatch patterns (e.g., ['*.test', '*-archive'])

        Returns:
            Filtered highwater data (items matching patterns are excluded)
        """
        import fnmatch

        filtered = {}

        for (domain, cos_name), data in highwater_data.items():
            # Check if domain matches any exclusion pattern
            excluded = False
            for pattern in patterns:
                if fnmatch.fnmatch(domain.lower(), pattern.lower()):
                    excluded = True
                    logger.debug(f"Excluding domain {domain} (matches pattern: {pattern})")
                    break

            if not excluded:
                filtered[(domain, cos_name)] = data

        logger.info(f"Filtered out {len(highwater_data) - len(filtered)} entries by domain pattern")
        return filtered

    def filter_by_cos_pattern(self, highwater_data: Dict[Tuple[str, str], Dict],
                             patterns: List[str]) -> Dict[Tuple[str, str], Dict]:
        """Filter highwater data by CoS patterns (for exclusions).

        Args:
            highwater_data: Highwater data to filter
            patterns: List of fnmatch patterns (e.g., ['*-test', '*-archive'])

        Returns:
            Filtered highwater data (items matching patterns are excluded)
        """
        import fnmatch

        filtered = {}

        for (domain, cos_name), data in highwater_data.items():
            # Check if CoS matches any exclusion pattern
            excluded = False
            for pattern in patterns:
                if fnmatch.fnmatch(cos_name.lower(), pattern.lower()):
                    excluded = True
                    logger.debug(f"Excluding CoS {cos_name} for domain {domain} (matches pattern: {pattern})")
                    break

            if not excluded:
                filtered[(domain, cos_name)] = data

        logger.info(f"Filtered out {len(highwater_data) - len(filtered)} entries by CoS pattern")
        return filtered


def calculate_monthly_highwater(parsed_reports: List[Dict]) -> Dict[Tuple[str, str], Dict]:
    """Convenience function to calculate monthly highwater marks.

    Args:
        parsed_reports: List of parsed report data

    Returns:
        Dictionary of highwater marks
    """
    calculator = HighwaterCalculator()
    return calculator.calculate_monthly_highwater(parsed_reports)


def process_month_reports(report_files: List[str]) -> Dict[Tuple[str, str], Dict]:
    """Process a month's worth of report files and calculate highwater marks.

    Args:
        report_files: List of paths to report files

    Returns:
        Dictionary of highwater marks
    """
    from .parser import ZimbraReportParser

    parser = ZimbraReportParser()
    calculator = HighwaterCalculator()

    # Parse all reports
    all_parsed_data = []
    for report_file in report_files:
        try:
            parsed_data = parser.parse_report_file(report_file)
            all_parsed_data.extend(parsed_data)
            logger.info(f"Parsed {len(parsed_data)} domains from {report_file}")
        except Exception as e:
            logger.error(f"Error parsing {report_file}: {e}")
            # Continue with other files

    # Calculate highwater marks
    highwater = calculator.calculate_monthly_highwater(all_parsed_data)

    # Log summary
    stats = calculator.get_summary_stats(highwater)
    logger.info(f"Monthly summary: {stats['total_domains']} domains, "
               f"{stats['total_accounts']} total accounts, "
               f"{stats['total_cos_types']} CoS types")

    return highwater
