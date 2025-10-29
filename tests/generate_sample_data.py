"""Generate sample Zimbra reports for testing."""

from datetime import datetime, timedelta
import random


def generate_sample_report(report_date: datetime, num_domains: int = 10) -> str:
    """Generate a sample Zimbra usage report.

    Args:
        report_date: Date for the report
        num_domains: Number of domains to include

    Returns:
        Report text in Zimbra format
    """
    cos_types = [
        'customer-50gb',
        'customer-20gb',
        'customer-10gb',
        'customer-100gb',
        'archive-50gb'
    ]

    domains = [
        'example.com',
        'test-company.com',
        'acme-corp.com',
        'widget-factory.com',
        'sample-domain.com',
        'mail.business.com',
        'email.enterprise.com',
        'messages.startup.com',
        'inbox.consulting.com',
        'mail.agency.com'
    ]

    report_lines = []

    for i in range(num_domains):
        domain = domains[i] if i < len(domains) else f'domain{i}.com'
        report_lines.append(domain)

        # Add 1-3 CoS entries per domain
        num_cos = random.randint(1, 3)
        cos_sample = random.sample(cos_types, num_cos)

        for cos in cos_sample:
            count = random.randint(1, 50)
            report_lines.append(f'    {cos}: {count}')

        report_lines.append('')  # Empty line between domains

    return '\n'.join(report_lines)


def generate_monthly_reports(year: int, month: int, output_dir: str = 'tests/sample_data') -> list:
    """Generate a month's worth of weekly reports.

    Args:
        year: Year
        month: Month
        output_dir: Directory to save reports

    Returns:
        List of generated file paths
    """
    import os
    from datetime import date
    from dateutil.relativedelta import relativedelta

    os.makedirs(output_dir, exist_ok=True)

    start_date = date(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    # Generate 4-5 weekly reports
    current_date = start_date
    report_files = []

    while current_date < end_date:
        # Generate report
        report_text = generate_sample_report(
            datetime.combine(current_date, datetime.min.time()),
            num_domains=10
        )

        # Save to file
        filename = f'usage_report_{current_date.strftime("%Y%m%d")}.txt'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            f.write(report_text)

        report_files.append(filepath)
        print(f"Generated: {filepath}")

        # Move to next week
        current_date += timedelta(days=7)

    return report_files


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    else:
        # Default to last month
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1

    print(f"Generating sample reports for {year}-{month:02d}")
    files = generate_monthly_reports(year, month)
    print(f"\nGenerated {len(files)} sample reports")
