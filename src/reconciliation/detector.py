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
            List of new domain names
        """
        # Get all known domains from database
        known_domains = self.session.query(Domain.domain_name).all()
        known_domain_set = {d[0] for d in known_domains}

        # Find new domains
        new_domains = current_domains - known_domain_set

        logger.info(f"Found {len(new_domains)} new domains")
        return sorted(list(new_domains))

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
            List of reappeared domain names
        """
        # Get domains that exist in DB but were marked inactive
        inactive_domains = self.session.query(Domain).filter(
            Domain.active.is_(False)
        ).all()

        reappeared = []
        for domain in inactive_domains:
            if domain.domain_name in current_domains:
                reappeared.append(domain.domain_name)

        logger.info(f"Found {len(reappeared)} reappearing domains")
        return reappeared

    def find_new_cos(self, current_cos_names: Set[str]) -> List[str]:
        """Find CoS names that don't have mappings.

        Args:
            current_cos_names: Set of CoS names from current reports

        Returns:
            List of unmapped CoS names
        """
        # Get all mapped CoS names
        mapped_cos = self.session.query(CoSMapping.cos_name).all()
        mapped_cos_set = {c[0] for c in mapped_cos}

        # Find new CoS
        new_cos = current_cos_names - mapped_cos_set

        logger.info(f"Found {len(new_cos)} unmapped CoS types")
        return sorted(list(new_cos))

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

    def detect_all_changes(self, current_data: Dict, year: int, month: int) -> Dict:
        """Run all change detection and return comprehensive results.

        Args:
            current_data: Dictionary with 'domains' and 'cos_names' sets
            year: Current year
            month: Current month

        Returns:
            Dictionary with all detected changes:
            {
                'new_domains': [...],
                'missing_domains': [...],
                'reappearing_domains': [...],
                'new_cos': [...],
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
        }

        # Determine if manual attention is needed
        changes['needs_attention'] = (
            len(changes['new_domains']) > 0 or
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
