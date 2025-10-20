# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""SQLAlchemy database models for Zimbra-QBO billing system."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Customer(Base):
    """QuickBooks Online customer records."""

    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    qbo_customer_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)
    active = Column(Boolean, default=True)

    # Relationships
    domains = relationship("Domain", back_populates="customer")
    invoices = relationship("InvoiceHistory", back_populates="customer")
    settings = relationship("CustomerSetting", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.customer_name}', qbo_id='{self.qbo_customer_id}')>"


class Domain(Base):
    """Domain to customer mappings."""

    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    domain_name = Column(String(255), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    notes = Column(Text)

    # Relationships
    customer = relationship("Customer", back_populates="domains")
    usage_data = relationship("UsageData", back_populates="domain")
    monthly_highwater = relationship("MonthlyHighwater", back_populates="domain")
    history = relationship("DomainHistory", back_populates="domain")

    __table_args__ = (
        Index('idx_domain_customer', 'domain_name', 'customer_id'),
    )

    def __repr__(self):
        return f"<Domain(id={self.id}, name='{self.domain_name}', customer_id={self.customer_id})>"


class Exclusion(Base):
    """Patterns for domains/CoS to exclude from billing."""

    __tablename__ = 'exclusions'

    id = Column(Integer, primary_key=True)
    exclusion_type = Column(String(20), nullable=False)  # 'domain' or 'cos'
    pattern = Column(String(255), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("exclusion_type IN ('domain', 'cos')", name='check_exclusion_type'),
        UniqueConstraint('exclusion_type', 'pattern', name='unique_exclusion'),
    )

    def __repr__(self):
        return f"<Exclusion(type='{self.exclusion_type}', pattern='{self.pattern}')>"


class CoSMapping(Base):
    """Class of Service to QuickBooks item mappings with pricing."""

    __tablename__ = 'cos_mappings'

    id = Column(Integer, primary_key=True)
    cos_name = Column(String(255), unique=True, nullable=False, index=True)
    qbo_item_id = Column(String(50), nullable=False)
    qbo_item_name = Column(String(255), nullable=False)
    unit_price = Column(Float, nullable=False)
    quota_gb = Column(Integer)  # Extracted from CoS name (e.g., 'customer-50gb' -> 50)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

    # Relationships
    usage_data = relationship("UsageData", back_populates="cos_mapping")
    monthly_highwater = relationship("MonthlyHighwater", back_populates="cos_mapping")
    cos_discovery = relationship("CoSDiscovery", back_populates="cos_mapping")

    def __repr__(self):
        return f"<CoSMapping(cos='{self.cos_name}', price=${self.unit_price}, quota={self.quota_gb}GB)>"


class UsageData(Base):
    """Raw weekly usage data from Zimbra reports."""

    __tablename__ = 'usage_data'

    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    cos_id = Column(Integer, ForeignKey('cos_mappings.id'), nullable=False)
    account_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    domain = relationship("Domain", back_populates="usage_data")
    cos_mapping = relationship("CoSMapping", back_populates="usage_data")

    __table_args__ = (
        UniqueConstraint('report_date', 'domain_id', 'cos_id', name='unique_usage_record'),
        Index('idx_usage_date_domain', 'report_date', 'domain_id'),
    )

    def __repr__(self):
        return f"<UsageData(date={self.report_date}, domain_id={self.domain_id}, cos_id={self.cos_id}, count={self.account_count})>"


class MonthlyHighwater(Base):
    """Monthly high-water mark calculations for billing."""

    __tablename__ = 'monthly_highwater'

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    cos_id = Column(Integer, ForeignKey('cos_mappings.id'), nullable=False)
    highwater_count = Column(Integer, nullable=False)
    billable = Column(Boolean, default=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    domain = relationship("Domain", back_populates="monthly_highwater")
    cos_mapping = relationship("CoSMapping", back_populates="monthly_highwater")

    __table_args__ = (
        UniqueConstraint('year', 'month', 'domain_id', 'cos_id', name='unique_monthly_highwater'),
        Index('idx_highwater_month', 'year', 'month'),
        CheckConstraint('month >= 1 AND month <= 12', name='check_valid_month'),
    )

    def __repr__(self):
        return f"<MonthlyHighwater({self.year}-{self.month:02d}, domain_id={self.domain_id}, cos_id={self.cos_id}, count={self.highwater_count})>"


class InvoiceHistory(Base):
    """History of invoices generated in QuickBooks."""

    __tablename__ = 'invoice_history'

    id = Column(Integer, primary_key=True)
    qbo_invoice_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    billing_year = Column(Integer, nullable=False)
    billing_month = Column(Integer, nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False)
    line_items_count = Column(Integer)
    status = Column(String(20), default='draft')  # draft, sent, paid, void
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")

    __table_args__ = (
        Index('idx_invoice_billing_period', 'billing_year', 'billing_month'),
        CheckConstraint('billing_month >= 1 AND billing_month <= 12', name='check_valid_billing_month'),
    )

    def __repr__(self):
        return f"<InvoiceHistory(qbo_id='{self.qbo_invoice_id}', period={self.billing_year}-{self.billing_month:02d}, amount=${self.total_amount})>"


class CustomerSetting(Base):
    """Per-customer billing settings and preferences."""

    __tablename__ = 'customer_settings'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), unique=True, nullable=False)
    bill_partial_months = Column(Boolean, default=False)
    custom_pricing = Column(Boolean, default=False)
    billing_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="settings")

    def __repr__(self):
        return f"<CustomerSetting(customer_id={self.customer_id}, bill_partial={self.bill_partial_months})>"


class DomainHistory(Base):
    """Historical tracking of domain status changes."""

    __tablename__ = 'domain_history'

    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    event_type = Column(String(20), nullable=False)  # 'discovered', 'assigned', 'disappeared', 'reappeared'
    event_date = Column(DateTime, default=datetime.utcnow, index=True)
    old_customer_id = Column(Integer, ForeignKey('customers.id'))
    new_customer_id = Column(Integer, ForeignKey('customers.id'))
    notes = Column(Text)

    # Relationships
    domain = relationship("Domain", back_populates="history")

    __table_args__ = (
        CheckConstraint("event_type IN ('discovered', 'assigned', 'disappeared', 'reappeared', 'moved')",
                       name='check_event_type'),
        Index('idx_domain_history_date', 'domain_id', 'event_date'),
    )

    def __repr__(self):
        return f"<DomainHistory(domain_id={self.domain_id}, event='{self.event_type}', date={self.event_date})>"


class CoSDiscovery(Base):
    """Tracking of newly discovered CoS patterns."""

    __tablename__ = 'cos_discovery'

    id = Column(Integer, primary_key=True)
    cos_name = Column(String(255), nullable=False, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    domain_count = Column(Integer, default=1)
    mapped = Column(Boolean, default=False)
    cos_mapping_id = Column(Integer, ForeignKey('cos_mappings.id'))
    notes = Column(Text)

    # Relationships
    cos_mapping = relationship("CoSMapping", back_populates="cos_discovery")

    def __repr__(self):
        return f"<CoSDiscovery(cos='{self.cos_name}', first_seen={self.first_seen}, mapped={self.mapped})>"


class ChangeLog(Base):
    """Audit log of user decisions and system changes."""

    __tablename__ = 'change_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    change_type = Column(String(50), nullable=False)  # 'domain_assignment', 'cos_mapping', 'exclusion_added', etc.
    entity_type = Column(String(50))  # 'domain', 'cos', 'customer', etc.
    entity_id = Column(Integer)
    description = Column(Text, nullable=False)
    user_decision = Column(Boolean, default=False)  # True if this was a user prompt response
    change_metadata = Column(Text)  # JSON string for additional context

    __table_args__ = (
        Index('idx_changelog_type_date', 'change_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<ChangeLog(type='{self.change_type}', time={self.timestamp}, user_decision={self.user_decision})>"
