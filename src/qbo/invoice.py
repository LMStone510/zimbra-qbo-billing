# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Invoice generation for QuickBooks Online.

Handles the logic of converting usage data into QBO invoices.
"""

import logging
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .client import QBOClient
from ..database.queries import QueryHelper
from ..database.models import MonthlyHighwater, InvoiceHistory

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """Generates invoices in QBO from usage data."""

    def __init__(self, qbo_client: QBOClient, query_helper: QueryHelper):
        """Initialize invoice generator.

        Args:
            qbo_client: QBO API client
            query_helper: Database query helper
        """
        self.qbo_client = qbo_client
        self.query_helper = query_helper

    def generate_invoice_for_customer(self, customer_id: int, year: int, month: int,
                                     draft: bool = True) -> Optional[str]:
        """Generate invoice for a customer based on monthly usage.

        Args:
            customer_id: Database customer ID
            year: Billing year
            month: Billing month
            draft: If True, create as draft invoice

        Returns:
            QBO invoice ID or None if no billable usage
        """
        logger.info(f"Generating invoice for customer {customer_id} for {year}-{month:02d}")

        # Get customer
        from ..database.models import Customer
        customer = self.query_helper.session.get(Customer, customer_id)

        if not customer:
            logger.error(f"Customer {customer_id} not found")
            return None

        # Generate idempotency key
        idempotency_key = self._generate_idempotency_key(customer.qbo_customer_id, year, month)

        # Check if invoice already exists for this period
        existing_invoice = self.query_helper.session.query(InvoiceHistory).filter(
            InvoiceHistory.idempotency_key == idempotency_key
        ).first()

        if existing_invoice:
            logger.info(
                f"Invoice already exists for customer {customer_id} "
                f"for {year}-{month:02d} (QBO ID: {existing_invoice.qbo_invoice_id}). "
                f"Skipping duplicate creation."
            )
            return existing_invoice.qbo_invoice_id

        # Get domains for customer
        domains = self.query_helper.get_domains_for_customer(customer_id)

        if not domains:
            logger.warning(f"No domains found for customer {customer_id}")
            return None

        # Collect usage data
        line_items = []
        total_amount = 0.0

        for domain in domains:
            # Get highwater marks for this domain
            highwater_records = self.query_helper.session.query(MonthlyHighwater).filter(
                MonthlyHighwater.year == year,
                MonthlyHighwater.month == month,
                MonthlyHighwater.domain_id == domain.id,
                MonthlyHighwater.billable.is_(True)
            ).all()

            for hw in highwater_records:
                cos_mapping = self.query_helper.get_cos_mapping_by_id(hw.cos_id)

                if not cos_mapping:
                    logger.warning(f"CoS mapping {hw.cos_id} not found")
                    continue

                # Create line item
                # Note: Price is automatically pulled from QBO item definition
                quantity = hw.highwater_count

                description = f"{domain.domain_name} - {cos_mapping.cos_name}"
                if cos_mapping.quota_gb:
                    description += f" ({cos_mapping.quota_gb}GB)"

                line_items.append({
                    'item_id': cos_mapping.qbo_item_id,
                    'quantity': quantity,
                    'description': description
                })

                # We can't calculate total_amount here since we don't fetch prices
                # QBO will calculate it based on item prices

        if not line_items:
            logger.info(f"No billable usage for customer {customer_id}")
            return None

        # Generate invoice memo
        memo = f"Zimbra Email Services - {self._get_month_name(month)} {year}"

        # Set invoice date (first of next month)
        if month == 12:
            invoice_date = date(year + 1, 1, 1)
        else:
            invoice_date = date(year, month + 1, 1)

        # Create invoice in QBO
        try:
            invoice = self.qbo_client.create_invoice(
                customer_id=customer.qbo_customer_id,
                line_items=line_items,
                invoice_date=datetime.combine(invoice_date, datetime.min.time()),
                memo=memo,
                draft=draft
            )

            # Get the actual total from the created invoice (QBO calculated it)
            actual_total = float(invoice.TotalAmt)

            # Record in invoice history
            self._record_invoice_history(
                qbo_invoice_id=invoice.Id,
                customer_id=customer_id,
                year=year,
                month=month,
                total_amount=actual_total,
                line_items_count=len(line_items),
                idempotency_key=idempotency_key
            )

            logger.info(f"Created invoice {invoice.Id} for ${actual_total:.2f}")
            return invoice.Id

        except Exception as e:
            logger.error(f"Error creating invoice for customer {customer_id}: {e}")
            raise

    def generate_all_invoices(self, year: int, month: int, draft: bool = True) -> Dict[str, List]:
        """Generate invoices for all customers with billable usage.

        Args:
            year: Billing year
            month: Billing month
            draft: If True, create as draft invoices

        Returns:
            Dictionary with 'success' and 'failed' lists of customer IDs
        """
        logger.info(f"Generating invoices for all customers for {year}-{month:02d}")

        # Get all customers with billable usage this month
        customers_with_usage = self._get_customers_with_usage(year, month)

        results = {
            'success': [],
            'failed': []
        }

        for customer_id in customers_with_usage:
            try:
                invoice_id = self.generate_invoice_for_customer(
                    customer_id, year, month, draft
                )

                if invoice_id:
                    results['success'].append({
                        'customer_id': customer_id,
                        'invoice_id': invoice_id
                    })
                else:
                    logger.warning(f"No invoice generated for customer {customer_id}")

            except Exception as e:
                logger.error(f"Failed to generate invoice for customer {customer_id}: {e}")
                results['failed'].append({
                    'customer_id': customer_id,
                    'error': str(e)
                })

        logger.info(
            f"Invoice generation complete: "
            f"{len(results['success'])} successful, "
            f"{len(results['failed'])} failed"
        )

        return results

    def preview_invoice_for_customer(self, customer_id: int, year: int, month: int) -> Dict:
        """Preview invoice data without creating it.

        Args:
            customer_id: Database customer ID
            year: Billing year
            month: Billing month

        Returns:
            Dictionary with invoice preview data
        """
        from ..database.models import Customer

        customer = self.query_helper.session.get(Customer, customer_id)

        if not customer:
            return {'error': 'Customer not found'}

        domains = self.query_helper.get_domains_for_customer(customer_id)

        line_items = []
        total_amount = 0.0

        for domain in domains:
            highwater_records = self.query_helper.session.query(MonthlyHighwater).filter(
                MonthlyHighwater.year == year,
                MonthlyHighwater.month == month,
                MonthlyHighwater.domain_id == domain.id,
                MonthlyHighwater.billable.is_(True)
            ).all()

            for hw in highwater_records:
                cos_mapping = self.query_helper.get_cos_mapping_by_id(hw.cos_id)

                if not cos_mapping:
                    continue

                # Fetch current price from QBO
                qbo_item = self.qbo_client.get_item_by_id(cos_mapping.qbo_item_id)
                unit_price = float(getattr(qbo_item, 'UnitPrice', 0)) if qbo_item else 0

                quantity = hw.highwater_count
                amount = quantity * unit_price

                line_items.append({
                    'domain': domain.domain_name,
                    'cos': cos_mapping.cos_name,
                    'quota_gb': cos_mapping.quota_gb,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'amount': amount
                })

                total_amount += amount

        return {
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'qbo_customer_id': customer.qbo_customer_id,
            'billing_period': f"{year}-{month:02d}",
            'line_items': line_items,
            'total_amount': total_amount,
            'line_count': len(line_items)
        }

    def get_invoice_summary(self, year: int, month: int) -> Dict:
        """Get summary of all invoices for a billing period.

        Args:
            year: Year
            month: Month

        Returns:
            Summary dictionary
        """
        customers_with_usage = self._get_customers_with_usage(year, month)

        total_customers = len(customers_with_usage)
        total_amount = 0.0
        total_line_items = 0

        for customer_id in customers_with_usage:
            preview = self.preview_invoice_for_customer(customer_id, year, month)
            if 'total_amount' in preview:
                total_amount += preview['total_amount']
                total_line_items += preview['line_count']

        return {
            'billing_period': f"{year}-{month:02d}",
            'total_customers': total_customers,
            'total_amount': total_amount,
            'total_line_items': total_line_items,
            'average_per_customer': total_amount / total_customers if total_customers > 0 else 0
        }

    def _get_customers_with_usage(self, year: int, month: int) -> List[int]:
        """Get list of customer IDs with billable usage for the month.

        Args:
            year: Year
            month: Month

        Returns:
            List of customer IDs
        """
        from ..database.models import Domain

        # Get all billable highwater records
        highwater_records = self.query_helper.get_highwater_for_month(
            year, month, billable_only=True
        )

        # Collect unique customer IDs
        customer_ids = set()
        for hw in highwater_records:
            domain = self.query_helper.session.get(Domain, hw.domain_id)
            if domain:
                customer_ids.add(domain.customer_id)

        return sorted(list(customer_ids))

    def _record_invoice_history(self, qbo_invoice_id: str, customer_id: int,
                                year: int, month: int, total_amount: float,
                                line_items_count: int, idempotency_key: str) -> None:
        """Record invoice in history table.

        Args:
            qbo_invoice_id: QBO invoice ID
            customer_id: Customer ID
            year: Billing year
            month: Billing month
            total_amount: Total invoice amount
            line_items_count: Number of line items
            idempotency_key: Unique key to prevent duplicates
        """
        history = InvoiceHistory(
            qbo_invoice_id=qbo_invoice_id,
            customer_id=customer_id,
            billing_year=year,
            billing_month=month,
            invoice_date=datetime.utcnow(),
            total_amount=total_amount,
            line_items_count=line_items_count,
            status='draft',
            idempotency_key=idempotency_key
        )

        self.query_helper.session.add(history)
        self.query_helper.session.commit()

        logger.debug(f"Recorded invoice {qbo_invoice_id} in history with idempotency key {idempotency_key}")

    def _get_month_name(self, month: int) -> str:
        """Get month name from number.

        Args:
            month: Month number (1-12)

        Returns:
            Month name
        """
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[month - 1] if 1 <= month <= 12 else str(month)

    def _generate_idempotency_key(self, qbo_customer_id: str, year: int, month: int) -> str:
        """Generate a unique idempotency key for invoice creation.

        The key is based on QBO customer ID, year, and month to ensure each
        customer gets at most one invoice per billing period.

        Args:
            qbo_customer_id: QuickBooks customer ID
            year: Billing year
            month: Billing month

        Returns:
            Idempotency key string
        """
        # Create a deterministic key from the inputs
        key_string = f"{qbo_customer_id}|{year}|{month:02d}"
        # Hash it for consistent length and to avoid special characters
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:32]
        return f"inv_{year}{month:02d}_{key_hash}"
