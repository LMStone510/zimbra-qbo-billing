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

## Low Priority (Future Consideration)

### 4. CLI Namespace Improvements

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

### Immediate (Next Release)
1. Add Dependabot configuration
2. Document token refresh testing procedure

### Next Quarter
1. Implement migration verification tests
2. Add token refresh integration tests

### Future (As Needed)
1. CLI namespace improvements (only if user base grows)

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

- Original code review: ChatGPT analysis (January 2025)
- Dependabot docs: https://docs.github.com/en/code-security/dependabot
- Alembic migrations: https://alembic.sqlalchemy.org/
- SQLAlchemy testing: https://docs.sqlalchemy.org/en/20/core/metadata.html

---

**Last Updated**: January 2025
**Status**: Active maintenance
**Next Review**: Q2 2025
