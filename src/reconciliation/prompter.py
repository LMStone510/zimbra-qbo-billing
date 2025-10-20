# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Interactive prompts for reconciliation decisions.

Handles user interaction for:
- Domain to customer assignment
- CoS to QBO item mapping
- Billing decisions
"""

import logging
from typing import List, Dict, Optional, Tuple
import click

from ..database.models import Customer, CoSMapping

logger = logging.getLogger(__name__)


class ReconciliationPrompter:
    """Handles interactive prompts for reconciliation."""

    def __init__(self, query_helper, interactive: bool = True):
        """Initialize prompter.

        Args:
            query_helper: QueryHelper instance for database access
            interactive: If False, skip all prompts and return None/default values
        """
        self.query_helper = query_helper
        self.interactive = interactive
        self.skipped_items = []  # Track items skipped in non-interactive mode

    def prompt_customer_for_domain(self, domain_name: str, customers: List[Customer]) -> Optional[int]:
        """Prompt user to assign a domain to a customer.

        Args:
            domain_name: Domain name to assign
            customers: List of available customers

        Returns:
            Customer ID or None to skip
        """
        if not self.interactive:
            logger.warning(f"Skipping domain assignment in non-interactive mode: {domain_name}")
            self.skipped_items.append({
                'type': 'domain',
                'name': domain_name,
                'reason': 'Non-interactive mode - requires manual assignment'
            })
            return None

        click.echo(f"\n{'='*60}")
        click.echo(f"New domain found: {click.style(domain_name, fg='yellow', bold=True)}")
        click.echo(f"{'='*60}")

        # Check if we have any history or notes about this domain
        from .detector import ChangeDetector
        detector = ChangeDetector(self.query_helper.session)
        history = detector.get_domain_history_summary(domain_name)

        if history.get('exists') and history.get('notes'):
            click.echo(f"\nNotes: {history['notes']}")

        click.echo("\nAvailable customers:")
        click.echo(f"  0: Skip (don't assign)")

        for i, customer in enumerate(customers, 1):
            click.echo(f"  {i}: {customer.customer_name} (QBO ID: {customer.qbo_customer_id})")

        while True:
            try:
                choice = click.prompt("\nSelect customer number", type=int, default=0)

                if choice == 0:
                    click.echo(click.style("Skipping domain assignment", fg='yellow'))
                    return None
                elif 1 <= choice <= len(customers):
                    selected_customer = customers[choice - 1]
                    click.echo(
                        click.style(
                            f"✓ Assigned {domain_name} to {selected_customer.customer_name}",
                            fg='green'
                        )
                    )
                    return selected_customer.id
                else:
                    click.echo(click.style(f"Invalid choice. Please enter 0-{len(customers)}", fg='red'))
            except (ValueError, click.Abort):
                click.echo(click.style("\nOperation cancelled", fg='red'))
                return None

    def prompt_cos_mapping(self, cos_name: str, qbo_items: List[Dict]) -> Optional[Dict]:
        """Prompt user to map a CoS to a QBO item.

        Args:
            cos_name: CoS name to map
            qbo_items: List of QBO items [{'id': ..., 'name': ..., 'price': ...}, ...]

        Returns:
            Dictionary with mapping info or None to skip
        """
        if not self.interactive:
            logger.warning(f"Skipping CoS mapping in non-interactive mode: {cos_name}")
            self.skipped_items.append({
                'type': 'cos',
                'name': cos_name,
                'reason': 'Non-interactive mode - requires manual mapping'
            })
            return None

        click.echo(f"\n{'='*60}")
        click.echo(f"New Class of Service found: {click.style(cos_name, fg='cyan', bold=True)}")
        click.echo(f"{'='*60}")

        # Try to extract quota from CoS name
        from ..zimbra.parser import ZimbraReportParser
        parser = ZimbraReportParser()
        quota_gb = parser.extract_quota_from_cos(cos_name)

        if quota_gb:
            click.echo(f"Detected quota: {quota_gb} GB")

        click.echo("\nAvailable QuickBooks items:")
        click.echo(f"  0: Skip (don't map)")

        for i, item in enumerate(qbo_items, 1):
            price_str = f"${item.get('price', 0):.2f}" if item.get('price') else "No price"
            click.echo(f"  {i}: {item['name']} ({price_str})")

        while True:
            try:
                choice = click.prompt("\nSelect QBO item number", type=int, default=0)

                if choice == 0:
                    click.echo(click.style("Skipping CoS mapping", fg='yellow'))
                    return None
                elif 1 <= choice <= len(qbo_items):
                    selected_item = qbo_items[choice - 1]

                    # Prompt for custom price if needed
                    current_price = selected_item.get('price', 0.0)
                    price = click.prompt(
                        f"Price per unit",
                        type=float,
                        default=current_price
                    )

                    # Prompt for quota if not detected
                    if quota_gb is None:
                        quota_gb = click.prompt(
                            "Quota in GB (or 0 if not applicable)",
                            type=int,
                            default=0
                        )
                        if quota_gb == 0:
                            quota_gb = None

                    click.echo(
                        click.style(
                            f"✓ Mapped {cos_name} to {selected_item['name']} at ${price:.2f}",
                            fg='green'
                        )
                    )

                    return {
                        'qbo_item_id': selected_item['id'],
                        'qbo_item_name': selected_item['name'],
                        'unit_price': price,
                        'quota_gb': quota_gb
                    }
                else:
                    click.echo(click.style(f"Invalid choice. Please enter 0-{len(qbo_items)}", fg='red'))
            except (ValueError, click.Abort):
                click.echo(click.style("\nOperation cancelled", fg='red'))
                return None

    def prompt_bill_partial_month(self, domain_name: str, customer_name: str,
                                   first_seen_date: str) -> bool:
        """Ask if a newly appeared domain should be billed for partial month.

        Args:
            domain_name: Domain name
            customer_name: Customer name
            first_seen_date: Date when domain first appeared

        Returns:
            True if should bill, False otherwise
        """
        if not self.interactive:
            # Default to not billing partial months in non-interactive mode
            logger.info(f"Skipping partial month billing in non-interactive mode: {domain_name}")
            return False

        click.echo(f"\n{'='*60}")
        click.echo(f"Partial month billing decision")
        click.echo(f"{'='*60}")
        click.echo(f"Domain: {click.style(domain_name, fg='yellow')}")
        click.echo(f"Customer: {customer_name}")
        click.echo(f"First seen: {first_seen_date}")

        return click.confirm("\nBill for this partial month?", default=False)

    def prompt_exclusion_addition(self, pattern: str, pattern_type: str) -> Tuple[bool, Optional[str]]:
        """Ask if a pattern should be added to exclusions.

        Args:
            pattern: Pattern to exclude (domain or CoS)
            pattern_type: 'domain' or 'cos'

        Returns:
            Tuple of (should_exclude, reason)
        """
        click.echo(f"\n{'='*60}")
        click.echo(f"Add {pattern_type} exclusion pattern?")
        click.echo(f"{'='*60}")
        click.echo(f"Pattern: {click.style(pattern, fg='yellow')}")

        if click.confirm(f"\nAdd '{pattern}' to {pattern_type} exclusions?", default=False):
            reason = click.prompt("Reason for exclusion", default="User-defined exclusion")
            return True, reason

        return False, None

    def display_reconciliation_summary(self, changes: Dict) -> None:
        """Display summary of changes detected.

        Args:
            changes: Dictionary from ChangeDetector.detect_all_changes()
        """
        click.echo(f"\n{'='*60}")
        click.echo(click.style("RECONCILIATION SUMMARY", fg='blue', bold=True))
        click.echo(f"{'='*60}")

        # New domains
        if changes['new_domains']:
            click.echo(f"\n{click.style('New domains:', fg='green', bold=True)} {len(changes['new_domains'])}")
            for domain in changes['new_domains'][:10]:  # Show first 10
                click.echo(f"  • {domain}")
            if len(changes['new_domains']) > 10:
                click.echo(f"  ... and {len(changes['new_domains']) - 10} more")

        # Missing domains
        if changes['missing_domains']:
            click.echo(f"\n{click.style('Missing domains:', fg='red', bold=True)} {len(changes['missing_domains'])}")
            for domain in changes['missing_domains'][:10]:
                click.echo(f"  • {domain}")
            if len(changes['missing_domains']) > 10:
                click.echo(f"  ... and {len(changes['missing_domains']) - 10} more")

        # Reappearing domains
        if changes['reappearing_domains']:
            click.echo(f"\n{click.style('Reappearing domains:', fg='yellow', bold=True)} {len(changes['reappearing_domains'])}")
            for domain in changes['reappearing_domains']:
                click.echo(f"  • {domain}")

        # New CoS
        if changes['new_cos']:
            click.echo(f"\n{click.style('New CoS types:', fg='cyan', bold=True)} {len(changes['new_cos'])}")
            for cos in changes['new_cos']:
                click.echo(f"  • {cos}")

        click.echo(f"\n{'='*60}\n")

    def confirm_continue(self, message: str = "Continue with reconciliation?") -> bool:
        """Ask user to confirm continuing.

        Args:
            message: Confirmation message

        Returns:
            True if user confirms, False otherwise
        """
        if not self.interactive:
            # Auto-continue in non-interactive mode
            return True
        return click.confirm(message, default=True)

    def get_skipped_items(self) -> List[Dict]:
        """Get list of items skipped in non-interactive mode.

        Returns:
            List of dicts with skipped item information
        """
        return self.skipped_items

    def display_skipped_summary(self) -> None:
        """Display summary of items skipped in non-interactive mode."""
        if not self.skipped_items:
            return

        click.echo(f"\n{'='*60}")
        click.echo(click.style("SKIPPED ITEMS (Non-Interactive Mode)", fg='yellow', bold=True))
        click.echo(f"{'='*60}")

        domains = [item for item in self.skipped_items if item['type'] == 'domain']
        cos_items = [item for item in self.skipped_items if item['type'] == 'cos']

        if domains:
            click.echo(f"\n{click.style('Unmapped Domains:', fg='yellow', bold=True)} {len(domains)}")
            for item in domains[:20]:
                click.echo(f"  • {item['name']}")
            if len(domains) > 20:
                click.echo(f"  ... and {len(domains) - 20} more")

        if cos_items:
            click.echo(f"\n{click.style('Unmapped CoS:', fg='yellow', bold=True)} {len(cos_items)}")
            for item in cos_items[:20]:
                click.echo(f"  • {item['name']}")
            if len(cos_items) > 20:
                click.echo(f"  ... and {len(cos_items) - 20} more")

        click.echo(f"\n{click.style('⚠ Action Required:', fg='yellow', bold=True)}")
        click.echo("  Run manual reconciliation to map these items:")
        click.echo("    python -m src.ui.cli reconcile-domains")
        click.echo("    python -m src.ui.cli reconcile-cos")
        click.echo(f"\n{'='*60}\n")

    def prompt_batch_assignment(self, domains: List[str], customer_name: str) -> bool:
        """Prompt for batch assignment of multiple domains to one customer.

        Args:
            domains: List of domain names
            customer_name: Customer name

        Returns:
            True if user confirms batch assignment
        """
        click.echo(f"\n{'='*60}")
        click.echo("Batch domain assignment")
        click.echo(f"{'='*60}")
        click.echo(f"Assign these {len(domains)} domains to {click.style(customer_name, fg='green')}?")

        for domain in domains[:20]:  # Show first 20
            click.echo(f"  • {domain}")
        if len(domains) > 20:
            click.echo(f"  ... and {len(domains) - 20} more")

        return click.confirm(f"\nConfirm batch assignment?", default=False)

    def prompt_manual_entry(self, prompt_text: str, field_type: str = "text") -> Optional[str]:
        """Prompt for manual text entry.

        Args:
            prompt_text: Prompt to display
            field_type: Type of field ('text', 'email', 'number')

        Returns:
            User input or None
        """
        try:
            if field_type == "number":
                return str(click.prompt(prompt_text, type=float))
            else:
                return click.prompt(prompt_text, type=str)
        except (click.Abort, KeyboardInterrupt):
            return None

    def display_progress(self, current: int, total: int, item_name: str = "items") -> None:
        """Display progress indicator.

        Args:
            current: Current item number
            total: Total items
            item_name: Name of items being processed
        """
        percentage = (current / total * 100) if total > 0 else 0
        click.echo(f"Progress: {current}/{total} {item_name} ({percentage:.1f}%)")

    def display_error(self, message: str) -> None:
        """Display error message.

        Args:
            message: Error message
        """
        click.echo(click.style(f"✗ Error: {message}", fg='red', bold=True))

    def display_success(self, message: str) -> None:
        """Display success message.

        Args:
            message: Success message
        """
        click.echo(click.style(f"✓ {message}", fg='green'))

    def display_warning(self, message: str) -> None:
        """Display warning message.

        Args:
            message: Warning message
        """
        click.echo(click.style(f"⚠ Warning: {message}", fg='yellow'))
