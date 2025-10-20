# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""SSH/SCP fetcher for Zimbra usage reports.

Connects to Zimbra server via SSH to retrieve weekly usage reports.
"""

import logging
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Tuple
from dateutil.relativedelta import relativedelta

import paramiko
from paramiko import SSHClient, AutoAddPolicy

from ..config import get_config

logger = logging.getLogger(__name__)


class ZimbraFetcher:
    """Fetches usage reports from Zimbra server via SSH/SCP."""

    def __init__(self, host: Optional[str] = None, username: Optional[str] = None,
                 key_file: Optional[str] = None, port: int = 22,
                 report_path: Optional[str] = None):
        """Initialize Zimbra fetcher.

        Args:
            host: Zimbra server hostname (uses config if None)
            username: SSH username (uses config if None)
            key_file: Path to SSH private key (uses config if None)
            port: SSH port (default: 22)
            report_path: Path to reports on server (uses config if None)
        """
        config = get_config()

        self.host = host or config.get('zimbra.host')
        self.username = username or config.get('zimbra.username')
        self.key_file = key_file or config.get('zimbra.key_file')
        self.port = port or config.get('zimbra.port', 22)
        self.report_path = report_path or config.get('zimbra.report_path')

        # Expand user home directory in key_file path
        if self.key_file:
            self.key_file = os.path.expanduser(self.key_file)

        self.client: Optional[SSHClient] = None

    def connect(self) -> None:
        """Establish SSH connection to Zimbra server."""
        if not self.host:
            raise ValueError("Zimbra host not configured")

        logger.info(f"Connecting to Zimbra server {self.host} as {self.username}")

        self.client = SSHClient()
        self.client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            if self.key_file and os.path.exists(self.key_file):
                logger.debug(f"Using SSH key file: {self.key_file}")
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=30
                )
            else:
                logger.debug("Using SSH agent authentication")
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    timeout=30
                )

            logger.info("SSH connection established")

        except Exception as e:
            logger.error(f"Failed to connect to Zimbra server: {e}")
            raise

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("SSH connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def list_reports(self, year: Optional[int] = None, month: Optional[int] = None) -> List[str]:
        """List available report files on the server.

        Args:
            year: Optional year filter
            month: Optional month filter

        Returns:
            List of report filenames
        """
        if not self.client:
            raise RuntimeError("Not connected to server. Call connect() first.")

        try:
            # List files in report directory
            stdin, stdout, stderr = self.client.exec_command(f'ls -1 {self.report_path}')
            files = stdout.read().decode('utf-8').strip().split('\n')
            errors = stderr.read().decode('utf-8').strip()

            if errors:
                logger.warning(f"Errors listing reports: {errors}")

            # Filter by year/month if specified
            if year or month:
                filtered_files = []
                for filename in files:
                    if not filename:
                        continue

                    # Try to extract date from filename
                    file_date = self._extract_date_from_filename(filename)
                    if file_date:
                        if year and file_date.year != year:
                            continue
                        if month and file_date.month != month:
                            continue
                        filtered_files.append(filename)
                files = filtered_files

            logger.info(f"Found {len(files)} report files")
            return [f for f in files if f]  # Remove empty strings

        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            raise

    def fetch_report(self, filename: str, local_path: str) -> str:
        """Fetch a single report file from the server.

        Args:
            filename: Name of the report file on server
            local_path: Local directory to save the file

        Returns:
            Path to downloaded file
        """
        if not self.client:
            raise RuntimeError("Not connected to server. Call connect() first.")

        remote_file = f"{self.report_path}/{filename}"
        local_file = os.path.join(local_path, filename)

        logger.info(f"Fetching report {filename}")

        try:
            # Ensure local directory exists
            os.makedirs(local_path, exist_ok=True)

            # Use SFTP to download file
            sftp = self.client.open_sftp()
            sftp.get(remote_file, local_file)
            sftp.close()

            logger.info(f"Report saved to {local_file}")
            return local_file

        except Exception as e:
            logger.error(f"Error fetching report {filename}: {e}")
            raise

    def fetch_monthly_reports(self, year: int, month: int, local_path: Optional[str] = None) -> List[str]:
        """Fetch all weekly reports for a given month.

        Args:
            year: Year
            month: Month (1-12)
            local_path: Local directory to save files (uses temp dir if None)

        Returns:
            List of paths to downloaded files
        """
        if local_path is None:
            import tempfile
            local_path = tempfile.mkdtemp(prefix=f"zimbra_reports_{year}_{month:02d}_")

        logger.info(f"Fetching reports for {year}-{month:02d}")

        # Get date range for the month
        start_date = date(year, month, 1)
        end_date = start_date + relativedelta(months=1)

        # We want reports from ~4-5 weeks to ensure we cover the entire month
        # Get reports starting from the previous month's last week
        fetch_start = start_date - relativedelta(weeks=1)

        # List all reports for the time period
        all_reports = self.list_reports()

        # Filter reports for our date range
        relevant_reports = []
        for filename in all_reports:
            file_date = self._extract_date_from_filename(filename)
            if file_date and fetch_start <= file_date < end_date + relativedelta(weeks=1):
                relevant_reports.append((filename, file_date))

        # Sort by date
        relevant_reports.sort(key=lambda x: x[1])

        logger.info(f"Found {len(relevant_reports)} reports for {year}-{month:02d}")

        # Fetch each report
        downloaded_files = []
        for filename, _ in relevant_reports:
            try:
                local_file = self.fetch_report(filename, local_path)
                downloaded_files.append(local_file)
            except Exception as e:
                logger.warning(f"Failed to fetch {filename}: {e}")
                # Continue with other files

        logger.info(f"Successfully fetched {len(downloaded_files)} reports")
        return downloaded_files

    def fetch_latest_report(self, local_path: Optional[str] = None) -> Optional[str]:
        """Fetch the most recent report file.

        Args:
            local_path: Local directory to save file

        Returns:
            Path to downloaded file or None
        """
        if local_path is None:
            import tempfile
            local_path = tempfile.mkdtemp(prefix="zimbra_reports_")

        # List all reports
        all_reports = self.list_reports()

        if not all_reports:
            logger.warning("No reports found on server")
            return None

        # Parse dates and find latest
        dated_reports = []
        for filename in all_reports:
            file_date = self._extract_date_from_filename(filename)
            if file_date:
                dated_reports.append((filename, file_date))

        if not dated_reports:
            logger.warning("No reports with parseable dates found")
            return None

        # Sort by date and get latest
        dated_reports.sort(key=lambda x: x[1], reverse=True)
        latest_filename = dated_reports[0][0]

        logger.info(f"Latest report is {latest_filename}")
        return self.fetch_report(latest_filename, local_path)

    def _extract_date_from_filename(self, filename: str) -> Optional[date]:
        """Extract date from report filename.

        Supports formats like:
        - report_2025-10-14.txt
        - usage_20251014.txt
        - weekly_2025_10_14.txt

        Args:
            filename: Report filename

        Returns:
            Date object or None
        """
        # Pattern to match various date formats
        patterns = [
            r'(\d{4})[_-](\d{2})[_-](\d{2})',  # 2025-10-14 or 2025_10_14
            r'(\d{4})(\d{2})(\d{2})',           # 20251014
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return date(year, month, day)
                except (ValueError, IndexError):
                    continue

        return None

    def test_connection(self) -> bool:
        """Test SSH connection and report path access.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connect()

            # Test report path access
            stdin, stdout, stderr = self.client.exec_command(f'ls -ld {self.report_path}')
            output = stdout.read().decode('utf-8').strip()
            errors = stderr.read().decode('utf-8').strip()

            if errors:
                logger.error(f"Error accessing report path: {errors}")
                return False

            logger.info(f"Report path accessible: {output}")

            self.disconnect()
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def fetch_monthly_reports(year: int, month: int, local_path: Optional[str] = None) -> List[str]:
    """Convenience function to fetch monthly reports.

    Args:
        year: Year
        month: Month (1-12)
        local_path: Optional local directory to save files

    Returns:
        List of paths to downloaded files
    """
    with ZimbraFetcher() as fetcher:
        return fetcher.fetch_monthly_reports(year, month, local_path)
