# Future Improvements & Recommendations

This document tracks recommended improvements for future releases based on code reviews and best practices.

---

## High Priority

### 1. Dependabot for Dependency Management

**Status**: Recommended
**Effort**: Low
**Impact**: High (Security)

**Current State:**
- Dependencies use `>=` constraints (good!)
- Manual updates required

**Recommendation:**
Add GitHub Dependabot configuration:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

**Benefits:**
- Automatic security updates
- Dependency vulnerability alerts
- Automated PR creation for updates

---

## Medium Priority

### 2. Token Refresh Background Testing

**Status**: Recommended
**Effort**: Medium
**Impact**: Medium (Reliability)

**Current State:**
- `EncryptedTokenStore` correctly encrypts/decrypts tokens
- Token refresh works during normal operation
- No automated testing of long-running refresh cycles

**Recommendation:**
Add integration test for token refresh continuity:

```python
# tests/test_token_refresh.py
def test_token_refresh_cycle():
    """Test that tokens can be refreshed and decrypted across multiple cycles."""
    # 1. Store initial token
    # 2. Simulate token refresh
    # 3. Verify decryption works
    # 4. Repeat for multiple cycles
    # 5. Verify no encryption drift
```

**Benefits:**
- Catches encryption/decryption issues before production
- Validates token rotation mechanism
- Prevents OAuth failures

---

### 3. Migration Verification Tests

**Status**: Recommended
**Effort**: Medium
**Impact**: Medium (Maintenance)

**Current State:**
- SQLite migrations work correctly
- PostgreSQL conditional path exists
- No automated schema drift detection

**Recommendation:**
Add schema verification tests:

```python
# tests/test_migrations.py
def test_schema_matches_models():
    """Verify database schema matches SQLAlchemy models."""
    # 1. Run all migrations
    # 2. Introspect actual schema
    # 3. Compare with model definitions
    # 4. Assert no drift
```

**Tools to Consider:**
- Alembic's autogenerate for drift detection
- SQLAlchemy schema comparison utilities

**Benefits:**
- Prevents schema drift between migrations and models
- Catches forgotten migrations
- Improves database reliability

---

### 4. Domain Reconciliation Performance Optimization

**Status**: Future consideration
**Effort**: Medium
**Impact**: Medium (Performance at scale)

**Current State:**
- `find_missing_domains()` in ChangeDetector iterates over ORM objects in Python
- Works well for typical deployments (50-500 domains)
- Potential bottleneck for large deployments (1000+ domains)

**Recommendation:**
Optimize domain reconciliation queries using SQL joins:

```python
# Current approach (Python iteration):
for domain_name in report_domains:
    domain = query_helper.get_domain_by_name(domain_name)
    # Process...

# Optimized approach (single SQL query):
# Use LEFT JOIN on MonthlyHighwater + Domain
# Filter in SQL where customer_id IS NULL
```

**Benefits:**
- Significant performance improvement for large domain counts
- Reduced database round-trips
- Lower memory footprint

**When to implement:**
- If processing time exceeds 30 seconds for domain reconciliation
- If deployment has 1000+ domains
- If performance issues are reported

---

### 5. Bulk Insert Optimization for Usage Data

**Status**: Future consideration
**Effort**: Low
**Impact**: Medium (Performance)

**Current State:**
- Usage data imported via individual ORM inserts
- Works well for typical monthly reports (100-1000 records)
- Uses standard SQLAlchemy session.add() pattern

**Recommendation:**
Use bulk operations for large report imports:

```python
# Current approach:
for record in usage_records:
    usage_data = UsageData(...)
    session.add(usage_data)
session.commit()

# Optimized approach:
session.bulk_save_objects([
    UsageData(...) for record in usage_records
])
session.commit()
```

**Benefits:**
- 5-10x faster for large imports
- Reduced transaction overhead
- Better scalability

**When to implement:**
- If import time exceeds 1 minute
- If monthly reports contain 5000+ usage records
- As part of general performance tuning in Q2 2026

---

## Low Priority (Future Consideration)

### 6. QuickBooks API Optimization

**Status**: Future consideration
**Effort**: Medium
**Impact**: Low (Current usage is well within limits)

**Current State:**
- Items and Customers fetched per billing run
- No caching between API calls
- No exponential backoff for rate limits
- Current usage: ~100-200 requests per billing run
- QBO limits: 500 requests/minute (production)

**Recommendation:**

**A. Implement Response Caching:**
```python
class QBOClient:
    def __init__(self):
        self._item_cache = {}  # Cache for billing run duration
        self._customer_cache = {}

    def get_item(self, item_id):
        if item_id in self._item_cache:
            return self._item_cache[item_id]
        item = # ... fetch from QBO
        self._item_cache[item_id] = item
        return item
```

**B. Add Exponential Backoff:**
```python
def _rate_limit_with_backoff(self):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Make API call
            return result
        except RateLimitError:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    raise
```

**Benefits:**
- Reduced API calls (fewer charges on metered plans)
- More resilient to rate limit issues
- Faster invoice generation

**When to implement:**
- If API rate limit errors occur
- If invoice generation time becomes an issue
- If deployment grows to 500+ domains

---

### 7. CLI Namespace Improvements

**Status**: Future consideration
**Effort**: Medium (Breaking change)
**Impact**: Low (User experience)

**Current State:**
- All commands under single `cli` group
- Works well, clear structure

**Future Consideration:**
Consider top-level namespace for larger deployments:

```bash
# Current
python3 -m src.ui.cli run-monthly-billing

# Future option
zqbo billing run --month 1 --year 2025
zqbo reconcile domains
zqbo reconcile cos --review-all
```

**Benefits:**
- Clearer command grouping
- Better auto-completion
- More intuitive for new users

**Trade-offs:**
- Breaking change for existing users
- More complex CLI structure
- May be overkill for current scope

**Recommendation:** Keep current structure. Only consider if:
- User base grows significantly
- Multiple billing systems need integration
- Command count exceeds 15-20

---

## Completed Improvements

### ✅ 1. Exception Logging
**Completed**: v1.10.1
**Details**: Logging already optimized - uses `logger.warning()` for non-critical errors and `logger.exception()` only logged to files, not console.

### ✅ 2. Dynamic Pricing
**Completed**: v1.10.0
**Details**: Prices now fetched from QuickBooks at invoice time, eliminating sync issues.

### ✅ 3. Automatic CoS Management
**Completed**: v1.10.0
**Details**: System automatically detects and prompts for new, obsolete, and invalid CoS mappings.

### ✅ 4. Dependency Version Flexibility
**Completed**: v1.10.1
**Details**: Updated to use `>=` constraints for better compatibility and security updates.

### ✅ 5. ISO8601 Timestamps
**Completed**: v1.10.1
**Details**: JSON output now includes both ISO8601 and Unix timestamps for flexibility.

---

## Implementation Priority

### Q1 2026 (Next Release)
1. Add Dependabot configuration
2. Document token refresh testing procedure

### Q2 2026
1. Implement migration verification tests
2. Add token refresh integration tests
3. Consider bulk insert optimization for usage data (if needed)

### Future (As Performance Needs Dictate)
1. Domain reconciliation SQL optimization (if 1000+ domains)
2. QuickBooks API caching and rate limiting (if rate limits hit)
3. CLI namespace improvements (only if user base grows significantly)

---

## Contributing

When implementing these recommendations:

1. **Create an issue** on GitHub for tracking
2. **Reference this document** in the issue
3. **Update this document** when completed
4. **Add tests** for all new functionality
5. **Update documentation** as needed

---

## References

- Original code review: ChatGPT analysis (October 2025)
- Dependabot docs: https://docs.github.com/en/code-security/dependabot
- Alembic migrations: https://alembic.sqlalchemy.org/
- SQLAlchemy testing: https://docs.sqlalchemy.org/en/20/core/metadata.html

---

**Last Updated**: October 2025
**Status**: Active maintenance
**Next Review**: Q2 2026
