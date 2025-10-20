# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Database query functions for common operations."""

import logging
import fnmatch
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .models import (
    Customer, Domain, Exclusion, CoSMapping, UsageData,
    MonthlyHighwater, InvoiceHistory, CustomerSetting,
    DomainHistory, CoSDiscovery, ChangeLog
)

logger = logging.getLogger(__name__)


class QueryHelper:
    """Helper class for database queries."""

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    # Customer queries
    def get_all_customers(self, active_only: bool = True) -> List[Customer]:
        """Get all customers.

        Args:
            active_only: If True, only return active customers

        Returns:
            List of Customer objects
        """
        query = self.session.query(Customer)
        if active_only:
            query = query.filter(Customer.active == True)
        return query.order_by(Customer.customer_name).all()

    def get_customer_by_qbo_id(self, qbo_id: str) -> Optional[Customer]:
        """Get customer by QuickBooks ID.

        Args:
            qbo_id: QuickBooks customer ID

        Returns:
            Customer object or None
        """
        return self.session.query(Customer).filter(
            Customer.qbo_customer_id == qbo_id
        ).first()

    def create_or_update_customer(self, qbo_id: str, name: str) -> Customer:
        """Create or update a customer record.

        Args:
            qbo_id: QuickBooks customer ID
            name: Customer name

        Returns:
            Customer object
        """
        customer = self.get_customer_by_qbo_id(qbo_id)
        if customer:
            customer.customer_name = name
            customer.updated_at = datetime.utcnow()
            customer.last_synced = datetime.utcnow()
        else:
            customer = Customer(
                qbo_customer_id=qbo_id,
                customer_name=name,
                last_synced=datetime.utcnow()
            )
            self.session.add(customer)
        self.session.commit()
        return customer

    # Domain queries
    def get_domain_by_name(self, domain_name: str) -> Optional[Domain]:
        """Get domain by name.

        Args:
            domain_name: Domain name

        Returns:
            Domain object or None
        """
        return self.session.query(Domain).filter(
            Domain.domain_name == domain_name
        ).first()

    def get_domains_for_customer(self, customer_id: int) -> List[Domain]:
        """Get all domains for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of Domain objects
        """
        return self.session.query(Domain).filter(
            Domain.customer_id == customer_id,
            Domain.active == True
        ).order_by(Domain.domain_name).all()

    def get_unassigned_domains(self) -> List[str]:
        """Get list of domains not yet assigned to a customer.

        Returns:
            List of domain names
        """
        # Get all domains from recent usage data that aren't in domains table
        subquery = self.session.query(Domain.domain_name)
        recent_domains = self.session.query(UsageData.domain_id).distinct().all()

        # This is a simplified version - in practice, you'd join through the domain table
        # and find domains that exist in usage but not properly mapped
        return []

    def assign_domain_to_customer(self, domain_name: str, customer_id: int, notes: Optional[str] = None) -> Domain:
        """Assign a domain to a customer.

        Args:
            domain_name: Domain name
            customer_id: Customer ID
            notes: Optional notes

        Returns:
            Domain object
        """
        domain = self.get_domain_by_name(domain_name)
        old_customer_id = None

        if domain:
            old_customer_id = domain.customer_id
            domain.customer_id = customer_id
            domain.last_seen = datetime.utcnow()
            if notes:
                domain.notes = notes
        else:
            domain = Domain(
                domain_name=domain_name,
                customer_id=customer_id,
                notes=notes
            )
            self.session.add(domain)

        # Log the change
        self._log_domain_history(
            domain_name=domain_name,
            event_type='assigned' if not old_customer_id else 'moved',
            old_customer_id=old_customer_id,
            new_customer_id=customer_id
        )

        self.session.commit()
        return domain

    # Exclusion queries
    def is_domain_excluded(self, domain_name: str) -> bool:
        """Check if a domain matches any exclusion pattern.

        Args:
            domain_name: Domain name to check

        Returns:
            True if domain should be excluded
        """
        exclusions = self.session.query(Exclusion).filter(
            Exclusion.exclusion_type == 'domain',
            Exclusion.active == True
        ).all()

        for exclusion in exclusions:
            if fnmatch.fnmatch(domain_name.lower(), exclusion.pattern.lower()):
                return True
        return False

    def is_cos_excluded(self, cos_name: str) -> bool:
        """Check if a CoS matches any exclusion pattern.

        Args:
            cos_name: CoS name to check

        Returns:
            True if CoS should be excluded
        """
        exclusions = self.session.query(Exclusion).filter(
            Exclusion.exclusion_type == 'cos',
            Exclusion.active == True
        ).all()

        for exclusion in exclusions:
            if fnmatch.fnmatch(cos_name.lower(), exclusion.pattern.lower()):
                return True
        return False

    # CoS mapping queries
    def get_cos_mapping(self, cos_name: str) -> Optional[CoSMapping]:
        """Get CoS mapping by name.

        Args:
            cos_name: CoS name

        Returns:
            CoSMapping object or None
        """
        return self.session.query(CoSMapping).filter(
            CoSMapping.cos_name == cos_name,
            CoSMapping.active == True
        ).first()

    def get_all_cos_mappings(self, active_only: bool = True) -> List[CoSMapping]:
        """Get all CoS mappings.

        Args:
            active_only: If True, only return active mappings

        Returns:
            List of CoSMapping objects
        """
        query = self.session.query(CoSMapping)
        if active_only:
            query = query.filter(CoSMapping.active == True)
        return query.order_by(CoSMapping.cos_name).all()

    def create_cos_mapping(self, cos_name: str, qbo_item_id: str, qbo_item_name: str,
                          unit_price: float, quota_gb: Optional[int] = None,
                          description: Optional[str] = None) -> CoSMapping:
        """Create a new CoS mapping.

        Args:
            cos_name: CoS name
            qbo_item_id: QuickBooks item ID
            qbo_item_name: QuickBooks item name
            unit_price: Price per unit
            quota_gb: Optional quota in GB
            description: Optional description

        Returns:
            CoSMapping object
        """
        mapping = CoSMapping(
            cos_name=cos_name,
            qbo_item_id=qbo_item_id,
            qbo_item_name=qbo_item_name,
            unit_price=unit_price,
            quota_gb=quota_gb,
            description=description
        )
        self.session.add(mapping)
        self.session.commit()
        return mapping

    # Usage data queries
    def store_usage_data(self, report_date: datetime, domain_name: str,
                        cos_name: str, account_count: int) -> None:
        """Store usage data from a report.

        Args:
            report_date: Date of the report
            domain_name: Domain name
            cos_name: CoS name
            account_count: Number of accounts
        """
        # Get or create domain
        domain = self.get_domain_by_name(domain_name)
        if not domain:
            # Domain not assigned yet - skip or create placeholder
            logger.warning(f"Domain {domain_name} not assigned to customer, skipping usage data")
            return

        # Get or create CoS mapping
        cos_mapping = self.get_cos_mapping(cos_name)
        if not cos_mapping:
            # CoS not mapped yet - track as discovery
            self._track_cos_discovery(cos_name)
            logger.warning(f"CoS {cos_name} not mapped to QBO item, skipping usage data")
            return

        # Check for existing record
        existing = self.session.query(UsageData).filter(
            UsageData.report_date == report_date,
            UsageData.domain_id == domain.id,
            UsageData.cos_id == cos_mapping.id
        ).first()

        if existing:
            existing.account_count = account_count
        else:
            usage = UsageData(
                report_date=report_date,
                domain_id=domain.id,
                cos_id=cos_mapping.id,
                account_count=account_count
            )
            self.session.add(usage)

        domain.last_seen = datetime.utcnow()
        self.session.commit()

    def get_usage_for_month(self, year: int, month: int) -> List[UsageData]:
        """Get all usage data for a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of UsageData objects
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta

        start_date = date(year, month, 1)
        end_date = start_date + relativedelta(months=1)

        return self.session.query(UsageData).filter(
            UsageData.report_date >= start_date,
            UsageData.report_date < end_date
        ).all()

    # Monthly highwater queries
    def calculate_and_store_highwater(self, year: int, month: int) -> None:
        """Calculate and store monthly highwater marks.

        Args:
            year: Year
            month: Month (1-12)
        """
        usage_data = self.get_usage_for_month(year, month)

        # Group by domain and CoS, find maximum
        highwater_dict: Dict[Tuple[int, int], int] = {}

        for usage in usage_data:
            key = (usage.domain_id, usage.cos_id)
            if key not in highwater_dict:
                highwater_dict[key] = usage.account_count
            else:
                highwater_dict[key] = max(highwater_dict[key], usage.account_count)

        # Store highwater marks
        for (domain_id, cos_id), count in highwater_dict.items():
            domain = self.session.query(Domain).get(domain_id)
            cos = self.session.query(CoSMapping).get(cos_id)

            # Check if should be billable
            billable = not (
                self.is_domain_excluded(domain.domain_name) or
                self.is_cos_excluded(cos.cos_name)
            )

            # Check for existing record
            existing = self.session.query(MonthlyHighwater).filter(
                MonthlyHighwater.year == year,
                MonthlyHighwater.month == month,
                MonthlyHighwater.domain_id == domain_id,
                MonthlyHighwater.cos_id == cos_id
            ).first()

            if existing:
                existing.highwater_count = count
                existing.billable = billable
                existing.calculated_at = datetime.utcnow()
            else:
                highwater = MonthlyHighwater(
                    year=year,
                    month=month,
                    domain_id=domain_id,
                    cos_id=cos_id,
                    highwater_count=count,
                    billable=billable
                )
                self.session.add(highwater)

        self.session.commit()

    def get_highwater_for_month(self, year: int, month: int, billable_only: bool = False) -> List[MonthlyHighwater]:
        """Get highwater marks for a month.

        Args:
            year: Year
            month: Month (1-12)
            billable_only: If True, only return billable records

        Returns:
            List of MonthlyHighwater objects
        """
        query = self.session.query(MonthlyHighwater).filter(
            MonthlyHighwater.year == year,
            MonthlyHighwater.month == month
        )
        if billable_only:
            query = query.filter(MonthlyHighwater.billable == True)
        return query.all()

    # Helper methods
    def _log_domain_history(self, domain_name: str, event_type: str,
                           old_customer_id: Optional[int] = None,
                           new_customer_id: Optional[int] = None,
                           notes: Optional[str] = None) -> None:
        """Log domain history event.

        Args:
            domain_name: Domain name
            event_type: Type of event
            old_customer_id: Previous customer ID
            new_customer_id: New customer ID
            notes: Optional notes
        """
        domain = self.get_domain_by_name(domain_name)
        if domain:
            history = DomainHistory(
                domain_id=domain.id,
                event_type=event_type,
                old_customer_id=old_customer_id,
                new_customer_id=new_customer_id,
                notes=notes
            )
            self.session.add(history)

    def _track_cos_discovery(self, cos_name: str) -> None:
        """Track a newly discovered CoS.

        Args:
            cos_name: CoS name
        """
        discovery = self.session.query(CoSDiscovery).filter(
            CoSDiscovery.cos_name == cos_name
        ).first()

        if discovery:
            discovery.last_seen = datetime.utcnow()
            discovery.domain_count += 1
        else:
            discovery = CoSDiscovery(
                cos_name=cos_name,
                domain_count=1
            )
            self.session.add(discovery)

    def log_change(self, change_type: str, description: str,
                   entity_type: Optional[str] = None, entity_id: Optional[int] = None,
                   user_decision: bool = False, metadata: Optional[str] = None) -> None:
        """Log a change to the change log.

        Args:
            change_type: Type of change
            description: Description of change
            entity_type: Optional entity type
            entity_id: Optional entity ID
            user_decision: Whether this was a user decision
            metadata: Optional JSON metadata
        """
        change = ChangeLog(
            change_type=change_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            user_decision=user_decision,
            metadata=metadata
        )
        self.session.add(change)
        self.session.commit()
