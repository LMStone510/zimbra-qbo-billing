# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""QuickBooks Online API client wrapper.

Provides methods for interacting with QBO API including:
- Customer management
- Item/Product/Service queries
- Invoice creation and management
- Rate limiting and error handling
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal

import requests
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer as QBOCustomer
from quickbooks.objects.item import Item
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
from quickbooks.exceptions import QuickbooksException

from .auth import QBOAuthManager
from .errors import (
    QBOError, classify_qbo_error, retry_with_backoff,
    QBOAuthError, QBORateLimitError
)
from ..config import get_config

logger = logging.getLogger(__name__)


def _escape_qbo_query_string(value: str) -> str:
    """Escape special characters in QuickBooks query strings.

    QBO uses SQL-like syntax where single quotes, %, and _ have special meaning.

    Args:
        value: String to escape

    Returns:
        Escaped string safe for use in QBO queries
    """
    if not value:
        return value

    # Escape single quotes by doubling them (SQL standard)
    value = value.replace("'", "''")

    # Escape wildcards to prevent unintended pattern matching
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")

    # Limit length to prevent excessively long queries
    max_length = 255
    if len(value) > max_length:
        value = value[:max_length]

    return value


class QBOClient:
    """QuickBooks Online API client."""

    def __init__(self, auth_manager: Optional[QBOAuthManager] = None):
        """Initialize QBO client.

        Args:
            auth_manager: Optional auth manager (creates new if None)
        """
        self.auth_manager = auth_manager or QBOAuthManager()
        config = get_config()

        self.company_id = config.get('qbo.company_id')
        self.sandbox = config.get('qbo.sandbox', True)

        self._qb_client = None
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests for rate limiting

    def _get_client(self) -> QuickBooks:
        """Get authenticated QuickBooks client.

        Returns:
            QuickBooks client instance
        """
        if self._qb_client is None or not self.auth_manager.is_authorized():
            # Get fresh access token
            access_token = self.auth_manager.get_valid_access_token()

            # Create a minimal auth client object for the QuickBooks library
            from intuitlib.client import AuthClient
            from intuitlib.enums import Scopes

            auth_client = AuthClient(
                client_id=self.auth_manager.client_id,
                client_secret=self.auth_manager.client_secret,
                redirect_uri=self.auth_manager.redirect_uri,
                environment='sandbox' if self.sandbox else 'production',
            )

            # Set the access token
            auth_client.access_token = access_token

            # Create QB client
            self._qb_client = QuickBooks(
                auth_client=auth_client,
                company_id=self.company_id
            )

            logger.info(f"Created QBO client for company {self.company_id} (sandbox={self.sandbox})")

        return self._qb_client

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle API errors consistently with classification.

        Args:
            operation: Description of operation
            error: Exception that occurred

        Raises:
            QBOError: Classified error with retry information
        """
        # Classify the error
        qbo_error = classify_qbo_error(error, operation=operation)

        # Log with appropriate level
        if qbo_error.is_retryable():
            logger.warning(f"{operation} failed with retryable error: {qbo_error}")
        else:
            logger.error(f"{operation} failed with non-retryable error: {qbo_error}")

        if isinstance(error, QuickbooksException):
            logger.error(f"QBO Error details: {error.detail}")

        raise qbo_error

    # Customer operations
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def get_all_customers(self, active_only: bool = True) -> List[QBOCustomer]:
        """Get all customers from QuickBooks.

        Args:
            active_only: If True, only return active customers

        Returns:
            List of Customer objects
        """
        logger.info("Fetching all customers from QBO")
        self._rate_limit()

        try:
            client = self._get_client()

            if active_only:
                query = "SELECT * FROM Customer WHERE Active = true MAXRESULTS 1000"
            else:
                query = "SELECT * FROM Customer MAXRESULTS 1000"

            customers = QBOCustomer.query(query, qb=client)

            logger.info(f"Retrieved {len(customers)} customers")
            return customers

        except Exception as e:
            self._handle_error("get_all_customers", e)

    def get_customer_by_id(self, customer_id: str) -> Optional[QBOCustomer]:
        """Get a customer by ID.

        Args:
            customer_id: QBO customer ID

        Returns:
            Customer object or None
        """
        logger.debug(f"Fetching customer {customer_id}")
        self._rate_limit()

        try:
            client = self._get_client()
            customer = QBOCustomer.get(customer_id, qb=client)
            return customer

        except Exception as e:
            logger.warning(f"Customer {customer_id} not found: {e}")
            return None

    def search_customers(self, search_term: str) -> List[QBOCustomer]:
        """Search customers by name.

        Args:
            search_term: Search term

        Returns:
            List of matching customers
        """
        logger.debug(f"Searching customers for: {search_term}")
        self._rate_limit()

        try:
            client = self._get_client()
            # Escape search term to prevent query injection and malformed queries
            escaped_term = _escape_qbo_query_string(search_term)
            query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_term}%'"
            customers = QBOCustomer.query(query, qb=client)
            return customers

        except Exception as e:
            self._handle_error("search_customers", e)

    # Item operations
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def get_all_items(self, item_type: Optional[str] = None) -> List[Item]:
        """Get all items (products/services) from QuickBooks.

        Args:
            item_type: Optional filter by type ('Service', 'Inventory', etc.)

        Returns:
            List of Item objects
        """
        logger.info("Fetching all items from QBO")
        self._rate_limit()

        try:
            client = self._get_client()

            if item_type:
                query = f"SELECT * FROM Item WHERE Type = '{item_type}' AND Active = true"
            else:
                query = "SELECT * FROM Item WHERE Active = true"

            items = Item.query(query, qb=client)

            logger.info(f"Retrieved {len(items)} items")
            return items

        except Exception as e:
            self._handle_error("get_all_items", e)

    def get_item_by_id(self, item_id: str) -> Optional[Item]:
        """Get an item by ID.

        Args:
            item_id: QBO item ID

        Returns:
            Item object or None
        """
        logger.debug(f"Fetching item {item_id}")
        self._rate_limit()

        try:
            client = self._get_client()
            item = Item.get(item_id, qb=client)
            return item

        except Exception as e:
            logger.warning(f"Item {item_id} not found: {e}")
            return None

    # Invoice operations
    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def create_invoice(self, customer_id: str, line_items: List[Dict],
                      invoice_date: Optional[datetime] = None,
                      due_date: Optional[datetime] = None,
                      memo: Optional[str] = None,
                      draft: bool = True,
                      doc_number: Optional[str] = None) -> Invoice:
        """Create a new invoice in QuickBooks.

        This method handles only the QuickBooks API interaction. The caller is responsible
        for persisting invoice records to the local database (InvoiceHistory table) with
        appropriate idempotency keys to prevent duplicate invoice creation.

        Args:
            customer_id: QBO customer ID
            line_items: List of line item dicts:
                       [{'item_id': ..., 'quantity': ..., 'description': ...}, ...]
                       Note: Prices are automatically pulled from QBO item definitions
            invoice_date: Invoice date (uses today if None)
            due_date: Due date (optional)
            memo: Invoice memo/notes
            draft: If True, create as draft (recommended)
            doc_number: Invoice number (optional, will be auto-assigned if None)

        Returns:
            Created Invoice object

        Note:
            This method does NOT persist to InvoiceHistory. The calling code
            (typically InvoiceGenerator) must handle persistence with idempotency
            keys to ensure invoices are not duplicated on subsequent runs.
        """
        logger.info(f"Creating invoice for customer {customer_id} with {len(line_items)} line items")
        self._rate_limit()

        try:
            client = self._get_client()

            # Create invoice object
            invoice = Invoice()

            # Set customer reference
            from quickbooks.objects.base import Ref
            invoice.CustomerRef = Ref()
            invoice.CustomerRef.value = customer_id

            # Set invoice number if provided
            if doc_number:
                invoice.DocNumber = doc_number

            # Set dates
            if invoice_date:
                invoice.TxnDate = invoice_date.strftime('%Y-%m-%d')
            if due_date:
                invoice.DueDate = due_date.strftime('%Y-%m-%d')

            # Set customer memo (visible on printed invoice)
            if memo:
                from quickbooks.objects.base import CustomerMemo as QBOCustomerMemo
                invoice.CustomerMemo = QBOCustomerMemo()
                invoice.CustomerMemo.value = memo

            # Add line items
            invoice.Line = []
            for i, item_data in enumerate(line_items, 1):
                line = SalesItemLine()
                line.LineNum = i
                line.Description = item_data.get('description', '')

                # Fetch current price from QuickBooks item
                # We fetch at invoice-time to ensure we always use current prices
                item = self.get_item_by_id(item_data['item_id'])
                unit_price = Decimal(str(getattr(item, 'UnitPrice', 0))) if item else Decimal('0.00')
                quantity = item_data['quantity']

                # Calculate line amount (QBO requires this to match UnitPrice × Qty)
                line_amount = unit_price * Decimal(quantity)

                detail = SalesItemLineDetail()
                detail.ItemRef = Ref()
                detail.ItemRef.value = item_data['item_id']
                detail.Qty = quantity
                # QBO API expects float, convert from Decimal
                detail.UnitPrice = float(unit_price)

                # Set service date if provided in line item data
                if 'service_date' in item_data:
                    detail.ServiceDate = item_data['service_date'].strftime('%Y-%m-%d')

                line.SalesItemLineDetail = detail
                # QBO API expects float, convert from Decimal
                line.Amount = float(line_amount)
                invoice.Line.append(line)

            # Note: We don't set EmailStatus for draft invoices to avoid
            # requiring email addresses for all customers. Users can prepare
            # emails manually from QuickBooks interface after review.

            # Save invoice
            invoice.save(qb=client)

            # Re-fetch the invoice to get calculated fields like TotalAmt
            # The save() method may not populate all calculated fields
            invoice = Invoice.get(invoice.Id, qb=client)

            logger.info(f"Created invoice {invoice.Id} for ${invoice.TotalAmt}")
            return invoice

        except Exception as e:
            self._handle_error("create_invoice", e)

    def get_invoice_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get an invoice by ID.

        Args:
            invoice_id: QBO invoice ID

        Returns:
            Invoice object or None
        """
        logger.debug(f"Fetching invoice {invoice_id}")
        self._rate_limit()

        try:
            client = self._get_client()
            invoice = Invoice.get(invoice_id, qb=client)
            return invoice

        except Exception as e:
            logger.warning(f"Invoice {invoice_id} not found: {e}")
            return None

    def query_invoices(self, customer_id: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> List[Invoice]:
        """Query invoices with filters.

        Args:
            customer_id: Optional customer ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of Invoice objects
        """
        logger.info("Querying invoices")
        self._rate_limit()

        try:
            client = self._get_client()

            # Build query
            conditions = []
            if customer_id:
                conditions.append(f"CustomerRef = '{customer_id}'")
            if start_date:
                conditions.append(f"TxnDate >= '{start_date.strftime('%Y-%m-%d')}'")
            if end_date:
                conditions.append(f"TxnDate <= '{end_date.strftime('%Y-%m-%d')}'")

            if conditions:
                query = "SELECT * FROM Invoice WHERE " + " AND ".join(conditions)
            else:
                query = "SELECT * FROM Invoice"

            invoices = Invoice.query(query, qb=client)

            logger.info(f"Retrieved {len(invoices)} invoices")
            return invoices

        except Exception as e:
            self._handle_error("query_invoices", e)

    def delete_invoice(self, invoice_id: str) -> bool:
        """Delete an invoice.

        Note: QBO doesn't truly delete, it voids the invoice.

        Args:
            invoice_id: Invoice ID to delete

        Returns:
            True if successful
        """
        logger.info(f"Voiding invoice {invoice_id}")
        self._rate_limit()

        try:
            client = self._get_client()
            invoice = Invoice.get(invoice_id, qb=client)

            # Void the invoice
            invoice.void(qb=client)

            logger.info(f"Successfully voided invoice {invoice_id}")
            return True

        except Exception as e:
            logger.error(f"Error voiding invoice {invoice_id}: {e}")
            return False

    # Utility methods
    def test_connection(self) -> bool:
        """Test connection to QBO API.

        Returns:
            True if connection successful
        """
        try:
            logger.info("Testing QBO connection")

            # Try to fetch company info as a simple test
            client = self._get_client()
            from quickbooks.objects.company_info import CompanyInfo

            company_info = CompanyInfo.get(1, qb=client)

            logger.info(f"Successfully connected to QBO: {company_info.CompanyName}")
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_company_info(self) -> Optional[Dict]:
        """Get company information.

        Returns:
            Dictionary with company info or None
        """
        try:
            client = self._get_client()
            from quickbooks.objects.company_info import CompanyInfo
            info = CompanyInfo.get(1, qb=client)

            return {
                'name': info.CompanyName,
                'email': getattr(info, 'Email', None),
                'company_id': self.company_id,
                'sandbox': self.sandbox
            }

        except Exception as e:
            logger.error(f"Error getting company info: {e}")
            return None

    def sync_customers_to_db(self, query_helper) -> int:
        """Sync QBO customers to local database.

        Args:
            query_helper: QueryHelper instance

        Returns:
            Number of customers synced
        """
        logger.info("Syncing QBO customers to database")

        customers = self.get_all_customers()
        count = 0

        for qbo_customer in customers:
            try:
                query_helper.create_or_update_customer(
                    qbo_id=qbo_customer.Id,
                    name=qbo_customer.DisplayName
                )
                count += 1
            except Exception as e:
                logger.warning(f"Error syncing customer {qbo_customer.Id}: {e}")

        logger.info(f"Synced {count} customers to database")
        return count


def get_qbo_client() -> QBOClient:
    """Get a QBO client instance.

    Returns:
        QBOClient instance
    """
    return QBOClient()
