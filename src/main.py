# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Main application orchestration for Zimbra-QBO billing automation.

Coordinates the complete monthly billing workflow:
1. Fetch Zimbra reports
2. Parse and calculate high-water marks
3. Run reconciliation (interactive)
4. Generate QBO invoices
5. Create Excel report
6. Display summary
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

import click

from .config import get_config
from .database.migrations import get_db_manager, init_database
from .database.queries import QueryHelper
from .zimbra.fetcher import ZimbraFetcher
from .zimbra.parser import ZimbraReportParser
from .zimbra.calculator import HighwaterCalculator
from .reconciliation.detector import ChangeDetector, extract_current_data
from .reconciliation.prompter import ReconciliationPrompter
from .reconciliation.mapper import MappingManager
from .qbo.client import get_qbo_client
from .qbo.invoice import InvoiceGenerator
from .reporting.excel import generate_monthly_report

logger = logging.getLogger(__name__)


def run_monthly_billing(year: int, month: int, skip_fetch: bool = False,
                       skip_reconciliation: bool = False, skip_invoices: bool = False,
                       draft: bool = True, non_interactive: bool = False,
                       json_output: Optional[str] = None) -> None:
    """Run the complete monthly billing workflow.

    Args:
        year: Billing year
        month: Billing month (1-12)
        skip_fetch: Skip fetching reports from Zimbra
        skip_reconciliation: Skip interactive reconciliation
        skip_invoices: Skip invoice generation
        draft: Create invoices as drafts
        non_interactive: Run in non-interactive mode (skip all prompts)
        json_output: Optional path to write JSON summary
    """
    logger.info(f"Starting monthly billing for {year}-{month:02d}")
    if non_interactive:
        logger.info("Running in non-interactive mode")

    # Initialize database
    db_manager = init_database()
    session = db_manager.get_session()
    query_helper = QueryHelper(session)

    try:
        # Step 1: Fetch reports from Zimbra
        if not skip_fetch:
            click.echo("\n[1/6] Fetching Zimbra reports...")
            report_files = fetch_reports(year, month)
            click.echo(f"      Retrieved {len(report_files)} report files")
        else:
            click.echo("\n[1/6] Skipping report fetch (using existing data)")
            report_files = []

        # Step 2: Parse reports and calculate highwater marks
        click.echo("\n[2/6] Processing reports and calculating usage...")
        if report_files:
            parsed_data, highwater_data = process_reports(report_files, query_helper, year, month)
            click.echo(f"      Processed {len(parsed_data)} domain records")
            click.echo(f"      Calculated {len(highwater_data)} highwater marks")
        else:
            # Use existing data from database
            highwater_records = query_helper.get_highwater_for_month(year, month)
            highwater_data = {}
            for hw in highwater_records:
                from .database.models import Domain
                domain = query_helper.session.get(Domain, hw.domain_id)
                cos = query_helper.get_cos_mapping_by_id(hw.cos_id)
                if domain and cos:
                    highwater_data[(domain.domain_name, cos.cos_name)] = {
                        'count': hw.highwater_count,
                        'dates': []
                    }
            click.echo(f"      Using existing {len(highwater_data)} highwater marks")

        # Step 3: Reconciliation
        if not skip_reconciliation:
            click.echo("\n[3/6] Running reconciliation...")
            prompter = run_reconciliation(highwater_data, query_helper, year, month, non_interactive)

            # Display skipped items summary if in non-interactive mode
            if non_interactive and prompter:
                prompter.display_skipped_summary()
        else:
            click.echo("\n[3/6] Skipping reconciliation")

        # Step 4: Generate invoices
        if not skip_invoices:
            click.echo("\n[4/6] Generating QuickBooks invoices...")
            invoice_results = generate_invoices(query_helper, year, month, draft)
            click.echo(f"      Created {len(invoice_results['success'])} invoices")
            if invoice_results['failed']:
                click.echo(click.style(
                    f"      {len(invoice_results['failed'])} invoices failed",
                    fg='yellow'
                ))
        else:
            click.echo("\n[4/6] Skipping invoice generation")
            invoice_results = {'success': [], 'failed': []}

        # Step 5: Generate Excel report
        click.echo("\n[5/6] Generating Excel report...")
        # Get QBO client to fetch current item prices for the report
        qbo_client = get_qbo_client()
        report_path = generate_monthly_report(year, month, query_helper, qbo_client=qbo_client)
        click.echo(f"      Report saved to: {report_path}")

        # Step 6: Display summary
        click.echo("\n[6/6] Billing Summary")
        display_summary(invoice_results, report_path, year, month, query_helper)

        # Generate JSON summary if requested
        if json_output:
            json_summary = generate_json_summary(
                invoice_results, report_path, year, month,
                query_helper, prompter if not skip_reconciliation else None
            )
            write_json_summary(json_summary, json_output)
            click.echo(f"\nJSON summary written to: {json_output}")

        session.commit()

    except Exception as e:
        session.rollback()
        logger.exception("Error during monthly billing")
        raise
    finally:
        session.close()


def fetch_reports(year: int, month: int) -> list:
    """Fetch Zimbra reports for the specified month.

    Args:
        year: Year
        month: Month

    Returns:
        List of downloaded report file paths
    """
    try:
        with ZimbraFetcher() as fetcher:
            report_files = fetcher.fetch_monthly_reports(year, month)
        logger.info(f"Fetched {len(report_files)} reports")
        return report_files
    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        raise


def process_reports(report_files: list, query_helper: QueryHelper,
                   year: int, month: int) -> tuple:
    """Parse reports and calculate highwater marks.

    Args:
        report_files: List of report file paths
        query_helper: Database query helper
        year: Year
        month: Month

    Returns:
        Tuple of (parsed_data, highwater_data)
    """
    parser = ZimbraReportParser()
    calculator = HighwaterCalculator()

    # Parse all reports
    all_parsed_data = []
    for report_file in report_files:
        try:
            parsed_data = parser.parse_report_file(report_file)
            all_parsed_data.extend(parsed_data)
        except Exception as e:
            logger.error(f"Error parsing {report_file}: {e}")

    # Calculate highwater marks
    highwater_data = calculator.calculate_monthly_highwater(all_parsed_data)

    # Store in database
    store_usage_data(all_parsed_data, query_helper)
    query_helper.calculate_and_store_highwater(year, month)

    return all_parsed_data, highwater_data


def store_usage_data(parsed_data: list, query_helper: QueryHelper) -> None:
    """Store parsed usage data in database.

    Args:
        parsed_data: List of parsed report records
        query_helper: Database query helper
    """
    for record in parsed_data:
        domain = record['domain']
        report_date = record['report_date']
        cos_usage = record['cos_usage']

        for cos_name, count in cos_usage.items():
            try:
                query_helper.store_usage_data(
                    report_date=report_date,
                    domain_name=domain,
                    cos_name=cos_name,
                    account_count=count
                )
            except Exception as e:
                logger.debug(f"Could not store usage for {domain}/{cos_name}: {e}")


def run_reconciliation(highwater_data: dict, query_helper: QueryHelper,
                      year: int, month: int, non_interactive: bool = False) -> Optional[ReconciliationPrompter]:
    """Run interactive reconciliation.

    Args:
        highwater_data: Highwater marks data
        query_helper: Database query helper
        year: Year
        month: Month
        non_interactive: Run in non-interactive mode

    Returns:
        ReconciliationPrompter instance (for accessing skipped items)
    """
    detector = ChangeDetector(query_helper.session)
    prompter = ReconciliationPrompter(query_helper, interactive=not non_interactive)
    mapper = MappingManager(query_helper)

    # Extract current domains and CoS
    current_data = extract_current_data(highwater_data)

    # Get QBO client for mapping validation
    qbo_client = get_qbo_client()

    # Detect changes (including validating QBO item mappings)
    changes = detector.detect_all_changes(current_data, year, month, qbo_client=qbo_client)

    # Display summary
    prompter.display_reconciliation_summary(changes)

    if not changes['needs_attention']:
        click.echo(click.style("No reconciliation needed", fg='green'))
        return

    if not prompter.confirm_continue():
        click.echo(click.style("Reconciliation cancelled", fg='yellow'))
        return

    # Reconcile new domains
    if changes['new_domains']:
        click.echo(f"\n--- Reconciling {len(changes['new_domains'])} new domains ---")
        customers = query_helper.get_all_customers()

        for domain_name in changes['new_domains']:
            # Check for suggestions
            suggested = mapper.suggest_customer_for_domain(domain_name)
            if suggested:
                click.echo(f"\nSuggested customer: {suggested.customer_name}")

            customer_id = prompter.prompt_customer_for_domain(domain_name, customers)
            if customer_id:
                mapper.map_domain_to_customer(domain_name, customer_id)

    # Handle obsolete CoS mappings
    if changes.get('obsolete_cos'):
        click.echo(f"\n--- Handling {len(changes['obsolete_cos'])} obsolete CoS mappings ---")
        for cos_info in changes['obsolete_cos']:
            if prompter.interactive:
                if click.confirm(f"Mark '{cos_info['cos_name']}' as inactive (no longer in Zimbra)?", default=True):
                    # Mark as inactive
                    cos_mapping = query_helper.session.get(CoSMapping, cos_info['mapping_id'])
                    if cos_mapping:
                        cos_mapping.active = False
                        query_helper.log_change(
                            'cos_mapping_deactivated',
                            f"Deactivated obsolete CoS mapping: {cos_info['cos_name']}",
                            'cos',
                            cos_info['mapping_id']
                        )
                        click.echo(click.style(f"  ✓ Deactivated {cos_info['cos_name']}", fg='yellow'))

    # Handle invalid QBO item mappings
    if changes.get('invalid_qbo_items'):
        click.echo(f"\n--- Handling {len(changes['invalid_qbo_items'])} invalid QBO item mappings ---")
        for item_info in changes['invalid_qbo_items']:
            click.echo(f"\n{item_info['cos_name']} → {item_info['qbo_item_name']}")
            click.echo(f"  Issue: {item_info['reason']}")
            if prompter.interactive:
                if click.confirm("  Remap this CoS to a different QBO item?", default=True):
                    # Get updated QBO items list
                    qbo_items = qbo_client.get_all_items(item_type='Service')
                    items_list = [
                        {'id': item.Id, 'name': item.Name, 'price': getattr(item, 'UnitPrice', 0)}
                        for item in qbo_items if getattr(item, 'Active', True)
                    ]
                    mapping_data = prompter.prompt_cos_mapping(item_info['cos_name'], items_list)
                    if mapping_data:
                        # Update existing mapping
                        cos_mapping = query_helper.session.get(CoSMapping, item_info['mapping_id'])
                        if cos_mapping:
                            cos_mapping.qbo_item_id = mapping_data['qbo_item_id']
                            cos_mapping.qbo_item_name = mapping_data['qbo_item_name']
                            if 'quota_gb' in mapping_data:
                                cos_mapping.quota_gb = mapping_data['quota_gb']
                            query_helper.log_change(
                                'cos_mapping_updated',
                                f"Updated CoS mapping: {item_info['cos_name']} → {mapping_data['qbo_item_name']}",
                                'cos',
                                item_info['mapping_id']
                            )

    # Reconcile new CoS
    if changes['new_cos']:
        click.echo(f"\n--- Reconciling {len(changes['new_cos'])} new CoS ---")

        # Get QBO items
        qbo_items = qbo_client.get_all_items(item_type='Service')
        items_list = [
            {'id': item.Id, 'name': item.Name, 'price': getattr(item, 'UnitPrice', 0)}
            for item in qbo_items
        ]

        for cos_name in changes['new_cos']:
            mapping_data = prompter.prompt_cos_mapping(cos_name, items_list)
            if mapping_data:
                mapper.map_cos_to_qbo_item(cos_name, **mapping_data)

    # Handle reappearing domains
    if changes['reappearing_domains']:
        click.echo(f"\n{len(changes['reappearing_domains'])} domains reappeared")
        for domain_name in changes['reappearing_domains']:
            domain = query_helper.get_domain_by_name(domain_name)
            if domain:
                domain.active = True
                query_helper.log_change(
                    'domain_reappeared',
                    f"Domain {domain_name} reappeared",
                    'domain',
                    domain.id
                )

    query_helper.session.commit()

    if non_interactive:
        skipped = prompter.get_skipped_items()
        if skipped:
            click.echo(click.style(
                f"\nReconciliation completed ({len(skipped)} items skipped in non-interactive mode)",
                fg='yellow'
            ))
        else:
            click.echo(click.style("\nReconciliation completed", fg='green'))
    else:
        click.echo(click.style("\nReconciliation completed", fg='green'))

    return prompter


def generate_invoices(query_helper: QueryHelper, year: int, month: int,
                     draft: bool = True) -> dict:
    """Generate invoices in QuickBooks.

    Args:
        query_helper: Database query helper
        year: Year
        month: Month
        draft: Create as drafts

    Returns:
        Dictionary with success/failed lists
    """
    qbo_client = get_qbo_client()
    generator = InvoiceGenerator(qbo_client, query_helper)

    results = generator.generate_all_invoices(year, month, draft)

    # Log results
    for success in results['success']:
        query_helper.log_change(
            'invoice_created',
            f"Created invoice {success['invoice_id']} for customer {success['customer_id']}",
            'invoice',
            success['customer_id']
        )

    return results


def display_summary(invoice_results: dict, report_path: str, year: int, month: int,
                   query_helper: QueryHelper) -> None:
    """Display billing summary.

    Args:
        invoice_results: Invoice generation results
        report_path: Path to Excel report
        year: Year
        month: Month
        query_helper: Database query helper
    """
    click.echo("\n" + "="*60)
    click.echo(click.style("BILLING SUMMARY", bold=True))
    click.echo("="*60)

    click.echo(f"\nBilling Period: {year}-{month:02d}")
    click.echo(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Invoice statistics
    success_count = len(invoice_results['success'])
    failed_count = len(invoice_results['failed'])

    click.echo(f"\nInvoices:")
    if success_count > 0:
        click.echo(click.style(f"  ✓ Created: {success_count}", fg='green'))
    if failed_count > 0:
        click.echo(click.style(f"  ✗ Failed: {failed_count}", fg='red'))

    # Calculate totals
    from .database.models import InvoiceHistory
    invoices = query_helper.session.query(InvoiceHistory).filter(
        InvoiceHistory.billing_year == year,
        InvoiceHistory.billing_month == month
    ).all()

    if invoices:
        total_amount = sum(inv.total_amount for inv in invoices)
        click.echo(f"\nTotal Amount: ${total_amount:,.2f}")

    click.echo(f"\nExcel Report: {report_path}")

    # Show failed invoices if any
    if failed_count > 0:
        click.echo(click.style("\nFailed Invoices:", fg='red', bold=True))
        for failed in invoice_results['failed']:
            click.echo(f"  Customer ID {failed['customer_id']}: {failed['error']}")

    click.echo("\n" + "="*60)


def generate_json_summary(invoice_results: dict, report_path: str, year: int, month: int,
                          query_helper: QueryHelper, prompter: Optional[ReconciliationPrompter] = None) -> dict:
    """Generate machine-readable JSON summary of billing run.

    Args:
        invoice_results: Invoice generation results
        report_path: Path to Excel report
        year: Year
        month: Month
        query_helper: Database query helper
        prompter: Optional reconciliation prompter (for skipped items)

    Returns:
        Dictionary with billing summary data
    """
    from .database.models import InvoiceHistory

    # Get invoice data
    invoices = query_helper.session.query(InvoiceHistory).filter(
        InvoiceHistory.billing_year == year,
        InvoiceHistory.billing_month == month
    ).all()

    invoice_details = []
    total_amount = 0.0

    for inv in invoices:
        invoice_details.append({
            'qbo_invoice_id': inv.qbo_invoice_id,
            'customer_id': inv.customer_id,
            'total_amount': inv.total_amount,
            'line_items_count': inv.line_items_count,
            'status': inv.status,
            'created_at': inv.created_at.isoformat() if inv.created_at else None
        })
        total_amount += inv.total_amount

    # Collect skipped items if available
    skipped_items = []
    if prompter:
        skipped_items = prompter.get_skipped_items()

    # Calculate runtime
    run_start = datetime.utcnow()

    summary = {
        'run_metadata': {
            'timestamp': run_start.isoformat() + 'Z',  # ISO8601 with UTC indicator
            'timestamp_unix': int(run_start.timestamp()),  # Unix timestamp for easy parsing
            'billing_period': {
                'year': year,
                'month': month
            },
            'version': '1.10.0'
        },
        'invoices': {
            'total_count': len(invoices),
            'success_count': len(invoice_results['success']),
            'failed_count': len(invoice_results['failed']),
            'total_amount': round(total_amount, 2),
            'average_amount': round(total_amount / len(invoices), 2) if invoices else 0,
            'details': invoice_details
        },
        'failures': [
            {
                'customer_id': f['customer_id'],
                'error': f['error']
            }
            for f in invoice_results['failed']
        ],
        'reconciliation': {
            'skipped_domains': len([i for i in skipped_items if i['type'] == 'domain']),
            'skipped_cos': len([i for i in skipped_items if i['type'] == 'cos']),
            'items': skipped_items
        },
        'reports': {
            'excel_path': report_path
        },
        'status': 'success' if not invoice_results['failed'] else 'partial_success'
    }

    return summary


def write_json_summary(summary: dict, output_path: str) -> None:
    """Write JSON summary to file.

    Args:
        summary: Summary dictionary
        output_path: Path to output file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"JSON summary written to {output_path}")


# Entry point for CLI
def main():
    """Main entry point."""
    from .ui.cli import cli
    cli()


if __name__ == '__main__':
    main()
