# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Mapping utilities for domains, CoS, and customers.

Maintains and queries mappings between:
- Domains and customers
- CoS and QBO items
- Pricing information
"""

import logging
from typing import Optional, List, Dict
import fnmatch

from ..database.queries import QueryHelper
from ..database.models import Domain, CoSMapping, Customer

logger = logging.getLogger(__name__)


class MappingManager:
    """Manages mappings between entities."""

    def __init__(self, query_helper: QueryHelper):
        """Initialize mapper.

        Args:
            query_helper: QueryHelper instance for database access
        """
        self.query_helper = query_helper

    def map_domain_to_customer(self, domain_name: str, customer_id: int,
                               notes: Optional[str] = None) -> Domain:
        """Map a domain to a customer.

        Args:
            domain_name: Domain name
            customer_id: Customer ID
            notes: Optional notes

        Returns:
            Domain object
        """
        logger.info(f"Mapping domain {domain_name} to customer ID {customer_id}")

        domain = self.query_helper.assign_domain_to_customer(
            domain_name=domain_name,
            customer_id=customer_id,
            notes=notes
        )

        # Log the change
        customer = self.query_helper.session.query(Customer).get(customer_id)
        self.query_helper.log_change(
            change_type='domain_assignment',
            description=f"Assigned domain '{domain_name}' to customer '{customer.customer_name}'",
            entity_type='domain',
            entity_id=domain.id,
            user_decision=True
        )

        return domain

    def map_cos_to_qbo_item(self, cos_name: str, qbo_item_id: str, qbo_item_name: str,
                            unit_price: float, quota_gb: Optional[int] = None,
                            description: Optional[str] = None) -> CoSMapping:
        """Map a CoS to a QBO item with pricing.

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
        logger.info(f"Mapping CoS {cos_name} to QBO item {qbo_item_name} at ${unit_price}")

        mapping = self.query_helper.create_cos_mapping(
            cos_name=cos_name,
            qbo_item_id=qbo_item_id,
            qbo_item_name=qbo_item_name,
            unit_price=unit_price,
            quota_gb=quota_gb,
            description=description
        )

        # Log the change
        self.query_helper.log_change(
            change_type='cos_mapping',
            description=f"Mapped CoS '{cos_name}' to QBO item '{qbo_item_name}' at ${unit_price}",
            entity_type='cos',
            entity_id=mapping.id,
            user_decision=True
        )

        return mapping

    def get_customer_for_domain(self, domain_name: str) -> Optional[Customer]:
        """Get the customer assigned to a domain.

        Args:
            domain_name: Domain name

        Returns:
            Customer object or None
        """
        domain = self.query_helper.get_domain_by_name(domain_name)
        if domain:
            return self.query_helper.session.query(Customer).get(domain.customer_id)
        return None

    def get_qbo_item_for_cos(self, cos_name: str) -> Optional[CoSMapping]:
        """Get the QBO item mapping for a CoS.

        Args:
            cos_name: CoS name

        Returns:
            CoSMapping object or None
        """
        return self.query_helper.get_cos_mapping(cos_name)

    def get_price_for_cos(self, cos_name: str) -> Optional[float]:
        """Get the unit price for a CoS.

        Args:
            cos_name: CoS name

        Returns:
            Unit price or None
        """
        mapping = self.query_helper.get_cos_mapping(cos_name)
        return mapping.unit_price if mapping else None

    def is_domain_excluded(self, domain_name: str) -> bool:
        """Check if a domain should be excluded from billing.

        Args:
            domain_name: Domain name

        Returns:
            True if domain should be excluded
        """
        return self.query_helper.is_domain_excluded(domain_name)

    def is_cos_excluded(self, cos_name: str) -> bool:
        """Check if a CoS should be excluded from billing.

        Args:
            cos_name: CoS name

        Returns:
            True if CoS should be excluded
        """
        return self.query_helper.is_cos_excluded(cos_name)

    def is_billable(self, domain_name: str, cos_name: str) -> bool:
        """Check if a domain/CoS combination is billable.

        Args:
            domain_name: Domain name
            cos_name: CoS name

        Returns:
            True if billable, False if excluded
        """
        if self.is_domain_excluded(domain_name):
            logger.debug(f"Domain {domain_name} is excluded")
            return False

        if self.is_cos_excluded(cos_name):
            logger.debug(f"CoS {cos_name} is excluded")
            return False

        # Check if domain is assigned to a customer
        domain = self.query_helper.get_domain_by_name(domain_name)
        if not domain:
            logger.debug(f"Domain {domain_name} not assigned to customer")
            return False

        # Check if CoS is mapped
        cos_mapping = self.query_helper.get_cos_mapping(cos_name)
        if not cos_mapping:
            logger.debug(f"CoS {cos_name} not mapped to QBO item")
            return False

        return True

    def get_all_mappings_summary(self) -> Dict:
        """Get summary of all mappings.

        Returns:
            Dictionary with mapping statistics
        """
        session = self.query_helper.session

        total_customers = session.query(Customer).filter(Customer.active == True).count()
        total_domains = session.query(Domain).filter(Domain.active == True).count()
        total_cos_mappings = session.query(CoSMapping).filter(CoSMapping.active == True).count()

        # Count unmapped items
        from ..database.models import Exclusion, CoSDiscovery
        unmapped_cos = session.query(CoSDiscovery).filter(CoSDiscovery.mapped == False).count()
        total_exclusions = session.query(Exclusion).filter(Exclusion.active == True).count()

        return {
            'total_customers': total_customers,
            'total_domains': total_domains,
            'total_cos_mappings': total_cos_mappings,
            'unmapped_cos': unmapped_cos,
            'total_exclusions': total_exclusions
        }

    def batch_assign_domains(self, domain_names: List[str], customer_id: int,
                            notes: Optional[str] = None) -> List[Domain]:
        """Assign multiple domains to a customer at once.

        Args:
            domain_names: List of domain names
            customer_id: Customer ID
            notes: Optional notes for all domains

        Returns:
            List of Domain objects
        """
        logger.info(f"Batch assigning {len(domain_names)} domains to customer ID {customer_id}")

        domains = []
        for domain_name in domain_names:
            try:
                domain = self.map_domain_to_customer(domain_name, customer_id, notes)
                domains.append(domain)
            except Exception as e:
                logger.error(f"Error assigning domain {domain_name}: {e}")
                # Continue with other domains

        logger.info(f"Successfully assigned {len(domains)} domains")
        return domains

    def find_similar_domains(self, domain_name: str, threshold: int = 3) -> List[str]:
        """Find domains similar to the given domain (for suggesting assignments).

        Args:
            domain_name: Domain name to find similar domains for
            threshold: Similarity threshold

        Returns:
            List of similar domain names
        """
        # Simple implementation: find domains with same root
        # (e.g., 'mail.example.com' and 'webmail.example.com')

        parts = domain_name.split('.')
        if len(parts) < 2:
            return []

        # Get the root domain (last two parts)
        root = '.'.join(parts[-2:])

        # Find all domains with same root
        all_domains = self.query_helper.session.query(Domain).filter(
            Domain.active == True
        ).all()

        similar = []
        for domain in all_domains:
            if domain.domain_name != domain_name and domain.domain_name.endswith(root):
                similar.append(domain.domain_name)

        return similar

    def suggest_customer_for_domain(self, domain_name: str) -> Optional[Customer]:
        """Suggest a customer for a domain based on similar domains.

        Args:
            domain_name: Domain name

        Returns:
            Customer object or None
        """
        similar_domains = self.find_similar_domains(domain_name)

        if not similar_domains:
            return None

        # Get customer for first similar domain
        similar_domain = self.query_helper.get_domain_by_name(similar_domains[0])
        if similar_domain:
            return self.query_helper.session.query(Customer).get(similar_domain.customer_id)

        return None

    def get_unmapped_items(self) -> Dict[str, List]:
        """Get all items that need mapping.

        Returns:
            Dictionary with 'domains' and 'cos' lists
        """
        session = self.query_helper.session

        # Find domains from usage data that aren't in domains table
        # This is simplified - would need actual query through usage_data
        from ..database.models import CoSDiscovery

        unmapped_cos = session.query(CoSDiscovery).filter(
            CoSDiscovery.mapped == False
        ).all()

        return {
            'domains': [],  # Would be populated with actual query
            'cos': [discovery.cos_name for discovery in unmapped_cos]
        }

    def validate_mappings(self) -> Dict[str, List]:
        """Validate all mappings and find issues.

        Returns:
            Dictionary with lists of issues by type
        """
        issues = {
            'domains_without_customer': [],
            'cos_without_mapping': [],
            'cos_without_price': [],
            'inactive_customer_domains': []
        }

        session = self.query_helper.session

        # Find domains without active customer
        domains = session.query(Domain).filter(Domain.active == True).all()
        for domain in domains:
            customer = session.query(Customer).get(domain.customer_id)
            if not customer or not customer.active:
                issues['inactive_customer_domains'].append(domain.domain_name)

        # Find CoS without price
        cos_mappings = session.query(CoSMapping).filter(CoSMapping.active == True).all()
        for mapping in cos_mappings:
            if mapping.unit_price <= 0:
                issues['cos_without_price'].append(mapping.cos_name)

        return issues
