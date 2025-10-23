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

import requests
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer as QBOCustomer
from quickbooks.objects.item import Item
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
from quickbooks.exceptions import QuickbooksException

from .auth import QBOAuthManager
from ..config import get_config

logger = logging.getLogger(__name__)


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
        """Handle API errors consistently.

        Args:
            operation: Description of operation
            error: Exception that occurred
        """
        logger.error(f"Error during {operation}: {error}")

        if isinstance(error, QuickbooksException):
            # QBO-specific error
            logger.error(f"QBO Error details: {error.detail}")

        raise

    # Customer operations
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
                query = "SELECT * FROM Customer WHERE Active = true"
            else:
                query = "SELECT * FROM Customer"

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
            query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{search_term}%'"
            customers = QBOCustomer.query(query, qb=client)
            return customers

        except Exception as e:
            self._handle_error("search_customers", e)

    # Item operations
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
    def create_invoice(self, customer_id: str, line_items: List[Dict],
                      invoice_date: Optional[datetime] = None,
                      due_date: Optional[datetime] = None,
                      memo: Optional[str] = None,
                      draft: bool = True) -> Invoice:
        """Create a new invoice.

        Args:
            customer_id: QBO customer ID
            line_items: List of line item dicts:
                       [{'item_id': ..., 'quantity': ..., 'description': ...}, ...]
                       Note: Prices are automatically pulled from QBO item definitions
            invoice_date: Invoice date (uses today if None)
            due_date: Due date (optional)
            memo: Invoice memo/notes
            draft: If True, create as draft (recommended)

        Returns:
            Created Invoice object
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

            # Set dates
            if invoice_date:
                invoice.TxnDate = invoice_date.strftime('%Y-%m-%d')
            if due_date:
                invoice.DueDate = due_date.strftime('%Y-%m-%d')

            # Set memo
            if memo:
                invoice.PrivateNote = memo

            # Add line items
            invoice.Line = []
            for i, item_data in enumerate(line_items, 1):
                line = SalesItemLine()
                line.LineNum = i
                line.Description = item_data.get('description', '')

                # Set item detail
                # NOTE: We only set ItemRef and Qty - QBO automatically uses
                # the price defined for the item in QuickBooks
                detail = SalesItemLineDetail()
                detail.ItemRef = Ref()
                detail.ItemRef.value = item_data['item_id']
                detail.Qty = item_data['quantity']

                line.SalesItemLineDetail = detail
                invoice.Line.append(line)

            # Set email status for draft invoices
            if draft:
                invoice.EmailStatus = "NeedToSend"

            # Save invoice
            invoice.save(qb=client)

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
