# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Command-line interface for Zimbra-QBO billing automation.

Provides CLI commands for:
- Running monthly billing workflow
- Manual reconciliation
- Report generation
- Configuration management
"""

import logging
import sys
from datetime import datetime

import click

from ..config import get_config, reload_config
from ..database.migrations import init_database, get_db_manager

logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(), help='Path to config file')
def cli(debug, config):
    """Zimbra to QuickBooks Online billing automation."""
    # Set up logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    if config:
        reload_config(config)

    # Initialize database if needed
    init_database()


@cli.command()
@click.option('--year', type=int, help='Billing year (default: current year)')
@click.option('--month', type=int, help='Billing month (default: last month)')
@click.option('--skip-fetch', is_flag=True, help='Skip fetching reports (use existing)')
@click.option('--skip-reconciliation', is_flag=True, help='Skip reconciliation prompts')
@click.option('--skip-invoices', is_flag=True, help='Skip invoice generation')
@click.option('--draft', is_flag=True, default=True, help='Create draft invoices (default)')
@click.option('--non-interactive', is_flag=True, help='Run in non-interactive mode (skip all prompts)')
@click.option('--json-output', type=click.Path(), help='Write JSON summary to file')
def run_monthly_billing(year, month, skip_fetch, skip_reconciliation, skip_invoices, draft, non_interactive, json_output):
    """Run the complete monthly billing workflow."""
    # Import here to avoid circular dependencies
    from ..main import run_monthly_billing as run_billing

    # Default to last month if not specified
    if not year or not month:
        now = datetime.now()
        if now.month == 1:
            year = year or (now.year - 1)
            month = month or 12
        else:
            year = year or now.year
            month = month or (now.month - 1)

    click.echo(f"\n{'='*60}")
    click.echo(f"Starting monthly billing for {year}-{month:02d}")
    if non_interactive:
        click.echo(click.style("Running in NON-INTERACTIVE mode", fg='yellow', bold=True))
    click.echo(f"{'='*60}\n")

    try:
        run_billing(
            year=year,
            month=month,
            skip_fetch=skip_fetch,
            skip_reconciliation=skip_reconciliation,
            skip_invoices=skip_invoices,
            draft=draft,
            non_interactive=non_interactive,
            json_output=json_output
        )

        click.echo(click.style("\n✓ Monthly billing completed successfully!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg='red', bold=True))
        logger.exception("Error running monthly billing")
        sys.exit(1)


@cli.command()
@click.option('--year', type=int, required=True, help='Report year')
@click.option('--month', type=int, required=True, help='Report month')
@click.option('--output', type=click.Path(), help='Output file path')
def generate_report(year, month, output):
    """Generate Excel billing report for a specific month."""
    from ..database.queries import QueryHelper
    from ..reporting.excel import generate_monthly_report
    from ..qbo.client import get_qbo_client

    click.echo(f"Generating report for {year}-{month:02d}...")

    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        query_helper = QueryHelper(session)

        # Get QBO client to fetch current item prices for the report
        qbo_client = get_qbo_client()
        report_path = generate_monthly_report(year, month, query_helper, output, qbo_client=qbo_client)

        click.echo(click.style(f"✓ Report generated: {report_path}", fg='green'))

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error generating report")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
def reconcile_domains():
    """Manually reconcile domains with customers."""
    from ..database.queries import QueryHelper
    from ..reconciliation.detector import ChangeDetector
    from ..reconciliation.prompter import ReconciliationPrompter
    from ..reconciliation.mapper import MappingManager

    click.echo("\nStarting domain reconciliation...\n")

    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        query_helper = QueryHelper(session)

        detector = ChangeDetector(session)
        prompter = ReconciliationPrompter(query_helper)
        mapper = MappingManager(query_helper)

        # Get list of new/unmapped domains
        # This is a simplified version - full implementation would scan usage data
        unmapped = mapper.get_unmapped_items()

        if not unmapped['domains']:
            click.echo(click.style("No unmapped domains found", fg='green'))
            return

        click.echo(f"Found {len(unmapped['domains'])} unmapped domains\n")

        # Get available customers
        customers = query_helper.get_all_customers()

        # Prompt for each domain
        for domain_name in unmapped['domains']:
            customer_id = prompter.prompt_customer_for_domain(domain_name, customers)
            if customer_id:
                mapper.map_domain_to_customer(domain_name, customer_id)

        session.commit()
        click.echo(click.style("\n✓ Domain reconciliation completed", fg='green'))

    except Exception as e:
        session.rollback()
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error during reconciliation")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.option('--review-all', is_flag=True, help='Review ALL mappings, not just unmapped CoS')
def reconcile_cos(review_all):
    """Manually reconcile CoS with QuickBooks items."""
    from ..database.queries import QueryHelper
    from ..reconciliation.prompter import ReconciliationPrompter
    from ..reconciliation.mapper import MappingManager
    from ..qbo.client import get_qbo_client
    from ..database.models import CoSMapping

    if review_all:
        click.echo("\nReviewing ALL CoS mappings...\n")
    else:
        click.echo("\nStarting CoS reconciliation...\n")

    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        query_helper = QueryHelper(session)

        prompter = ReconciliationPrompter(query_helper)
        mapper = MappingManager(query_helper)
        qbo_client = get_qbo_client()

        # Get QBO items
        qbo_items = qbo_client.get_all_items(item_type='Service')
        items_list = [
            {'id': item.Id, 'name': item.Name, 'price': getattr(item, 'UnitPrice', 0)}
            for item in qbo_items if getattr(item, 'Active', True)
        ]

        if review_all:
            # Review all existing mappings
            all_mappings = session.query(CoSMapping).filter(CoSMapping.active == True).all()

            if not all_mappings:
                click.echo(click.style("No existing CoS mappings found", fg='yellow'))
                return

            click.echo(f"Found {len(all_mappings)} existing CoS mappings to review\n")

            for existing_mapping in all_mappings:
                click.echo(f"\n{'='*60}")
                click.echo(f"Current mapping: {click.style(existing_mapping.cos_name, fg='cyan', bold=True)}")
                click.echo(f"  → QBO Item: {existing_mapping.qbo_item_name}")
                if existing_mapping.quota_gb:
                    click.echo(f"  → Quota: {existing_mapping.quota_gb} GB")

                # Get current price from QBO
                qbo_item = qbo_client.get_item_by_id(existing_mapping.qbo_item_id)
                if qbo_item:
                    current_price = float(getattr(qbo_item, 'UnitPrice', 0))
                    click.echo(f"  → Current QBO Price: ${current_price:.2f}")
                else:
                    click.echo(click.style(f"  ⚠ Warning: QBO item not found or inactive!", fg='red'))

                click.echo(f"{'='*60}")

                # Ask if user wants to change this mapping
                if click.confirm("\nChange this mapping?", default=False):
                    mapping_data = prompter.prompt_cos_mapping(existing_mapping.cos_name, items_list)
                    if mapping_data:
                        # Update the mapping
                        existing_mapping.qbo_item_id = mapping_data['qbo_item_id']
                        existing_mapping.qbo_item_name = mapping_data['qbo_item_name']
                        if 'quota_gb' in mapping_data:
                            existing_mapping.quota_gb = mapping_data['quota_gb']

                        query_helper.log_change(
                            'cos_mapping_updated',
                            f"Updated CoS mapping: {existing_mapping.cos_name} → {mapping_data['qbo_item_name']}",
                            'cos',
                            existing_mapping.id,
                            user_decision=True
                        )
                        click.echo(click.style("  ✓ Mapping updated", fg='green'))
                elif click.confirm("Mark this CoS as inactive (no longer used)?", default=False):
                    existing_mapping.active = False
                    query_helper.log_change(
                        'cos_mapping_deactivated',
                        f"Deactivated CoS mapping: {existing_mapping.cos_name}",
                        'cos',
                        existing_mapping.id,
                        user_decision=True
                    )
                    click.echo(click.style("  ✓ Mapping deactivated", fg='yellow'))
                else:
                    click.echo(click.style("  → Keeping current mapping", fg='cyan'))
        else:
            # Get unmapped CoS only
            unmapped = mapper.get_unmapped_items()

            if not unmapped['cos']:
                click.echo(click.style("No unmapped CoS found", fg='green'))
                click.echo("\nTip: Use --review-all to review existing mappings")
                return

            click.echo(f"Found {len(unmapped['cos'])} unmapped CoS\n")

            # Prompt for each CoS
            for cos_name in unmapped['cos']:
                mapping_data = prompter.prompt_cos_mapping(cos_name, items_list)
                if mapping_data:
                    mapper.map_cos_to_qbo_item(
                        cos_name=cos_name,
                        **mapping_data
                    )

        session.commit()
        click.echo(click.style("\n✓ CoS reconciliation completed", fg='green'))

    except Exception as e:
        session.rollback()
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error during CoS reconciliation")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
def sync_customers():
    """Sync customers from QuickBooks to local database."""
    from ..database.queries import QueryHelper
    from ..qbo.client import get_qbo_client

    click.echo("Syncing customers from QuickBooks...\n")

    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        query_helper = QueryHelper(session)
        qbo_client = get_qbo_client()

        count = qbo_client.sync_customers_to_db(query_helper)

        click.echo(click.style(f"✓ Synced {count} customers", fg='green'))

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error syncing customers")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
def authorize_qbo():
    """Authorize application with QuickBooks Online."""
    from ..qbo.auth import QBOAuthManager

    click.echo("\nQuickBooks Online Authorization\n")

    try:
        auth_manager = QBOAuthManager()
        auth_manager.authorize_interactive()

        click.echo(click.style("\n✓ Authorization successful!", fg='green'))
        click.echo("You can now use the application to generate invoices.")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error during authorization")
        sys.exit(1)


@cli.command()
def test_connections():
    """Test connections to Zimbra and QuickBooks."""
    click.echo("\nTesting connections...\n")

    # Test Zimbra
    click.echo("Testing Zimbra SSH connection...")
    try:
        from ..zimbra.fetcher import ZimbraFetcher
        fetcher = ZimbraFetcher()
        if fetcher.test_connection():
            click.echo(click.style("✓ Zimbra connection successful", fg='green'))
        else:
            click.echo(click.style("✗ Zimbra connection failed", fg='red'))
    except Exception as e:
        click.echo(click.style(f"✗ Zimbra error: {e}", fg='red'))

    # Test QBO
    click.echo("\nTesting QuickBooks Online connection...")
    try:
        from ..qbo.client import get_qbo_client
        qbo_client = get_qbo_client()
        if qbo_client.test_connection():
            company_info = qbo_client.get_company_info()
            click.echo(click.style(f"✓ QBO connection successful: {company_info['name']}", fg='green'))
        else:
            click.echo(click.style("✗ QBO connection failed", fg='red'))
    except Exception as e:
        click.echo(click.style(f"✗ QBO error: {e}", fg='red'))


@cli.command()
@click.option('--year', type=int, required=True, help='Year')
@click.option('--month', type=int, required=True, help='Month')
@click.option('--customer-id', type=int, help='Preview for specific customer')
def preview_invoices(year, month, customer_id):
    """Preview invoices without creating them."""
    from ..database.queries import QueryHelper
    from ..qbo.invoice import InvoiceGenerator
    from ..qbo.client import get_qbo_client

    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()
        query_helper = QueryHelper(session)
        qbo_client = get_qbo_client()

        generator = InvoiceGenerator(qbo_client, query_helper)

        if customer_id:
            # Preview single customer
            preview = generator.preview_invoice_for_customer(customer_id, year, month)

            click.echo(f"\nInvoice Preview for {preview['customer_name']}")
            click.echo(f"{'='*60}")
            click.echo(f"QBO Customer ID: {preview['qbo_customer_id']}")
            click.echo(f"Billing Period: {preview['billing_period']}")
            click.echo(f"Line Items: {preview['line_count']}")
            click.echo(f"Total Amount: ${preview['total_amount']:.2f}\n")

            if preview['line_items']:
                click.echo("Line Items:")
                for item in preview['line_items']:
                    click.echo(f"  {item['domain']} - {item['cos']}: "
                             f"{item['quantity']} × ${item['unit_price']:.2f} = ${item['amount']:.2f}")

        else:
            # Preview summary
            summary = generator.get_invoice_summary(year, month)

            click.echo(f"\nInvoice Summary for {summary['billing_period']}")
            click.echo(f"{'='*60}")
            click.echo(f"Total Customers: {summary['total_customers']}")
            click.echo(f"Total Line Items: {summary['total_line_items']}")
            click.echo(f"Total Amount: ${summary['total_amount']:.2f}")
            click.echo(f"Average per Customer: ${summary['average_per_customer']:.2f}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        logger.exception("Error previewing invoices")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
def init_db():
    """Initialize or reset the database."""
    click.echo("\nDatabase Initialization\n")

    if click.confirm("This will create/reset the database. Continue?", default=False):
        try:
            db_manager = get_db_manager()
            db_manager.initialize_database()

            click.echo(click.style("✓ Database initialized successfully", fg='green'))

        except Exception as e:
            click.echo(click.style(f"✗ Error: {e}", fg='red'))
            sys.exit(1)


if __name__ == '__main__':
    cli()
