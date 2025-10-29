# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Change detection for reconciliation.

Detects month-over-month changes in:
- New domains appearing
- Domains disappearing
- New CoS patterns
- New QBO customers
"""

import logging
from datetime import datetime
from typing import List, Dict, Set, Tuple
from sqlalchemy.orm import Session

from ..database.models import Domain, CoSMapping, Customer, MonthlyHighwater, CoSDiscovery
from ..database.queries import QueryHelper

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detects changes requiring reconciliation."""

    def __init__(self, session: Session):
        """Initialize detector with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.query_helper = QueryHelper(session)

    def find_new_domains(self, current_domains: Set[str]) -> List[str]:
        """Find domains that appear in current data but not in database.

        Args:
            current_domains: Set of domain names from current reports

        Returns:
            List of new domain names (excluding those in exclusion list)
        """
        # Get all known domains from database
        known_domains = self.session.query(Domain.domain_name).all()
        known_domain_set = {d[0] for d in known_domains}

        # Find new domains
        new_domains = current_domains - known_domain_set

        # Filter out excluded domains
        filtered_domains = []
        for domain_name in new_domains:
            if not self.query_helper.is_domain_excluded(domain_name):
                filtered_domains.append(domain_name)
            else:
                logger.debug(f"Excluding domain from reconciliation: {domain_name}")

        logger.info(f"Found {len(filtered_domains)} new domains (after excluding {len(new_domains) - len(filtered_domains)} excluded domains)")
        return sorted(filtered_domains)

    def find_missing_domains(self, current_domains: Set[str], year: int, month: int) -> List[str]:
        """Find domains that were active last month but missing this month.

        Args:
            current_domains: Set of domain names from current reports
            year: Current year
            month: Current month

        Returns:
            List of missing domain names
        """
        # Calculate previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        # Get domains from previous month's highwater
        prev_highwater = self.query_helper.get_highwater_for_month(prev_year, prev_month)
        prev_domains = set()

        for hw in prev_highwater:
            domain = self.session.get(Domain, hw.domain_id)
            if domain:
                prev_domains.add(domain.domain_name)

        # Find missing domains
        missing_domains = prev_domains - current_domains

        logger.info(f"Found {len(missing_domains)} missing domains (present last month, absent this month)")
        return sorted(list(missing_domains))

    def find_reappearing_domains(self, current_domains: Set[str]) -> List[str]:
        """Find domains that reappeared after being inactive.

        Args:
            current_domains: Set of domain names from current reports

        Returns:
            List of reappeared domain names (excluding those in exclusion list)
        """
        # Get domains that exist in DB but were marked inactive
        inactive_domains = self.session.query(Domain).filter(
            Domain.active.is_(False)
        ).all()

        reappeared = []
        for domain in inactive_domains:
            if domain.domain_name in current_domains:
                if not self.query_helper.is_domain_excluded(domain.domain_name):
                    reappeared.append(domain.domain_name)
                else:
                    logger.debug(f"Excluding reappearing domain from reconciliation: {domain.domain_name}")

        logger.info(f"Found {len(reappeared)} reappearing domains (after exclusions)")
        return reappeared

    def find_new_cos(self, current_cos_names: Set[str]) -> List[str]:
        """Find CoS names that don't have mappings.

        Args:
            current_cos_names: Set of CoS names from current reports

        Returns:
            List of unmapped CoS names (excluding those in exclusion list)
        """
        # Get all mapped CoS names
        mapped_cos = self.session.query(CoSMapping.cos_name).filter(
            CoSMapping.active.is_(True)
        ).all()
        mapped_cos_set = {c[0] for c in mapped_cos}

        # Find new CoS
        new_cos = current_cos_names - mapped_cos_set

        # Filter out excluded CoS
        filtered_cos = []
        for cos_name in new_cos:
            if not self.query_helper.is_cos_excluded(cos_name):
                filtered_cos.append(cos_name)
            else:
                logger.debug(f"Excluding CoS from reconciliation: {cos_name}")

        logger.info(f"Found {len(filtered_cos)} unmapped CoS types (after excluding {len(new_cos) - len(filtered_cos)} excluded CoS)")
        return sorted(filtered_cos)

    def find_obsolete_cos_mappings(self, current_cos_names: Set[str]) -> List[Dict]:
        """Find CoS mappings that no longer appear in Zimbra data.

        Args:
            current_cos_names: Set of CoS names from current reports

        Returns:
            List of dicts with obsolete mapping info
        """
        # Get all active mapped CoS names
        active_mappings = self.session.query(CoSMapping).filter(
            CoSMapping.active.is_(True)
        ).all()

        obsolete = []
        for mapping in active_mappings:
            if mapping.cos_name not in current_cos_names:
                obsolete.append({
                    'cos_name': mapping.cos_name,
                    'qbo_item_name': mapping.qbo_item_name,
                    'mapping_id': mapping.id
                })

        logger.info(f"Found {len(obsolete)} potentially obsolete CoS mappings")
        return obsolete

    def find_invalid_qbo_item_mappings(self, qbo_client) -> List[Dict]:
        """Find CoS mappings pointing to deleted/invalid QBO items.

        Args:
            qbo_client: QBO client instance

        Returns:
            List of dicts with invalid mapping info
        """
        active_mappings = self.session.query(CoSMapping).filter(
            CoSMapping.active.is_(True)
        ).all()

        invalid = []
        for mapping in active_mappings:
            # Try to fetch the QBO item
            qbo_item = qbo_client.get_item_by_id(mapping.qbo_item_id)
            if not qbo_item or not getattr(qbo_item, 'Active', True):
                invalid.append({
                    'cos_name': mapping.cos_name,
                    'qbo_item_id': mapping.qbo_item_id,
                    'qbo_item_name': mapping.qbo_item_name,
                    'mapping_id': mapping.id,
                    'reason': 'QBO item not found or inactive'
                })

        logger.info(f"Found {len(invalid)} CoS mappings with invalid QBO items")
        return invalid

    def find_new_qbo_customers(self, qbo_customer_ids: Set[str]) -> List[str]:
        """Find QBO customers that aren't in our database.

        Args:
            qbo_customer_ids: Set of customer IDs from QBO

        Returns:
            List of new customer IDs
        """
        # Get all known customer IDs
        known_customers = self.session.query(Customer.qbo_customer_id).all()
        known_customer_set = {c[0] for c in known_customers}

        # Find new customers
        new_customers = qbo_customer_ids - known_customer_set

        logger.info(f"Found {len(new_customers)} new QBO customers")
        return sorted(list(new_customers))

    def find_unassigned_domains(self) -> List[Dict]:
        """Find domains in usage data without customer assignments.

        Returns:
            List of dicts with domain info: [{'domain': 'example.com', 'first_seen': datetime, ...}]
        """
        # Get domains from CoS discovery that aren't mapped
        unmapped = self.session.query(CoSDiscovery).filter(
            CoSDiscovery.mapped.is_(False)
        ).all()

        # This is a simplified check - in real implementation, you'd join through usage_data
        # to find domains that have usage but aren't in the domains table

        unassigned = []
        # For now, return domains that exist but have no customer_id or are not properly set up
        # This would be expanded based on actual usage patterns

        return unassigned

    def detect_all_changes(self, current_data: Dict, year: int, month: int,
                          qbo_client=None) -> Dict:
        """Run all change detection and return comprehensive results.

        Args:
            current_data: Dictionary with 'domains' and 'cos_names' sets
            year: Current year
            month: Current month
            qbo_client: Optional QBO client for validating item mappings

        Returns:
            Dictionary with all detected changes:
            {
                'new_domains': [...],
                'missing_domains': [...],
                'reappearing_domains': [...],
                'new_cos': [...],
                'obsolete_cos': [...],
                'invalid_qbo_items': [...],
                'needs_attention': bool
            }
        """
        current_domains = current_data.get('domains', set())
        current_cos = current_data.get('cos_names', set())

        changes = {
            'new_domains': self.find_new_domains(current_domains),
            'missing_domains': self.find_missing_domains(current_domains, year, month),
            'reappearing_domains': self.find_reappearing_domains(current_domains),
            'new_cos': self.find_new_cos(current_cos),
            'obsolete_cos': self.find_obsolete_cos_mappings(current_cos),
            'invalid_qbo_items': []
        }

        # Optionally check for invalid QBO items (requires API calls)
        if qbo_client:
            changes['invalid_qbo_items'] = self.find_invalid_qbo_item_mappings(qbo_client)

        # Determine if manual attention is needed
        changes['needs_attention'] = (
            len(changes['new_domains']) > 0 or
            len(changes['new_cos']) > 0 or
            len(changes['obsolete_cos']) > 0 or
            len(changes['invalid_qbo_items']) > 0 or
            len(changes['new_cos']) > 0 or
            len(changes['reappearing_domains']) > 0
        )

        # Log summary
        logger.info(f"Change detection summary:")
        logger.info(f"  New domains: {len(changes['new_domains'])}")
        logger.info(f"  Missing domains: {len(changes['missing_domains'])}")
        logger.info(f"  Reappearing domains: {len(changes['reappearing_domains'])}")
        logger.info(f"  New CoS: {len(changes['new_cos'])}")
        logger.info(f"  Needs attention: {changes['needs_attention']}")

        return changes

    def get_domain_history_summary(self, domain_name: str) -> Dict:
        """Get historical summary for a domain.

        Args:
            domain_name: Domain name

        Returns:
            Dictionary with history info
        """
        domain = self.query_helper.get_domain_by_name(domain_name)

        if not domain:
            return {
                'exists': False,
                'domain_name': domain_name
            }

        # Get history records
        from ..database.models import DomainHistory
        history = self.session.query(DomainHistory).filter(
            DomainHistory.domain_id == domain.id
        ).order_by(DomainHistory.event_date.desc()).limit(10).all()

        return {
            'exists': True,
            'domain_name': domain_name,
            'customer_id': domain.customer_id,
            'first_seen': domain.first_seen,
            'last_seen': domain.last_seen,
            'active': domain.active,
            'notes': domain.notes,
            'history': [
                {
                    'event_type': h.event_type,
                    'event_date': h.event_date,
                    'notes': h.notes
                }
                for h in history
            ]
        }

    def get_cos_usage_stats(self, cos_name: str, year: int, month: int) -> Dict:
        """Get usage statistics for a CoS type.

        Args:
            cos_name: CoS name
            year: Year
            month: Month

        Returns:
            Dictionary with usage stats
        """
        # Get CoS mapping if it exists
        cos_mapping = self.query_helper.get_cos_mapping(cos_name)

        if not cos_mapping:
            return {
                'mapped': False,
                'cos_name': cos_name
            }

        # Get usage for this month
        highwater = self.session.query(MonthlyHighwater).filter(
            MonthlyHighwater.year == year,
            MonthlyHighwater.month == month,
            MonthlyHighwater.cos_id == cos_mapping.id
        ).all()

        total_count = sum(hw.highwater_count for hw in highwater)
        domain_count = len(highwater)

        return {
            'mapped': True,
            'cos_name': cos_name,
            'qbo_item_name': cos_mapping.qbo_item_name,
            'unit_price': cos_mapping.unit_price,
            'quota_gb': cos_mapping.quota_gb,
            'total_accounts': total_count,
            'domain_count': domain_count
        }


def extract_current_data(highwater_data: Dict[Tuple[str, str], Dict]) -> Dict:
    """Extract current domains and CoS names from highwater data.

    Args:
        highwater_data: Highwater data from calculator

    Returns:
        Dictionary with 'domains' and 'cos_names' sets
    """
    domains = set()
    cos_names = set()

    for (domain, cos_name), _ in highwater_data.items():
        domains.add(domain)
        cos_names.add(cos_name)

    return {
        'domains': domains,
        'cos_names': cos_names
    }
