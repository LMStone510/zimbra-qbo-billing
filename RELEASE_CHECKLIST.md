# Zimbra-QBO Billing v1.0.0 Production Release Checklist

This checklist ensures safe production deployment with proper validation, backup, and verification.

## 1️⃣ Pre-Deployment Validation

### 1.1 Code Integrity

- [ ] Confirm all changes committed to git
- [ ] Create release tag:
  ```bash
  git tag -a v1.0.0 -m "Production release - secure, idempotent billing"
  git push origin v1.0.0
  ```
- [ ] Verify working directory is clean: `git status`

### 1.2 Dependency Verification

- [ ] Lock dependencies:
  ```bash
  pip3 freeze > requirements-lock.txt
  ```
- [ ] Audit for vulnerabilities (optional):
  ```bash
  pip3 install safety
  safety check -r requirements.txt
  ```
- [ ] Verify Python version: `python3 --version` (>=3.8 required, >=3.11 recommended)

### 1.3 Installation Test

- [ ] Test clean installation:
  ```bash
  pip3 install -e .
  python3 -m src.ui.cli --help
  # Should show all commands
  ```

---

## 2️⃣ Database Preparation

### 2.1 Backup Existing Data

- [ ] Backup current database:
  ```bash
  # Create timestamped backup
  cp data/billing.db data/billing.db.$(date +%Y%m%d_%H%M%S)

  # Or backup to safe location
  cp data/billing.db /path/to/backups/billing_pre_v1.0.0.db
  ```
- [ ] Verify backup is readable:
  ```bash
  sqlite3 /path/to/backups/billing_pre_v1.0.0.db "SELECT COUNT(*) FROM customers;"
  ```

### 2.2 Apply Automatic Migrations

- [ ] Run migration (happens automatically):
  ```bash
  python3 -m src.ui.cli init-db
  ```
- [ ] Verify migration output shows:
  ```
  Checking for database migrations...
  All migrations complete
  ```

### 2.3 Verify Schema Changes

- [ ] Confirm idempotency_key column exists:
  ```bash
  sqlite3 data/billing.db "PRAGMA table_info(invoice_history);" | grep idempotency_key
  ```
- [ ] Check for unique index:
  ```bash
  sqlite3 data/billing.db "SELECT sql FROM sqlite_master WHERE name='idx_invoice_idempotency';"
  ```
  Should show: `CREATE UNIQUE INDEX idx_invoice_idempotency ON invoice_history(idempotency_key)`

---

## 3️⃣ Environment and Config Validation

### 3.1 Encrypted Token Store

- [ ] Verify OAuth tokens exist and are encrypted:
  ```bash
  ls -la data/qbo_tokens.enc data/.qbo_key
  ```
- [ ] Check file permissions (should be 600):
  ```bash
  # Should show: -rw------- (600)
  ls -la data/qbo_tokens.enc data/.qbo_key
  ```
- [ ] Test token validity:
  ```bash
  python3 -m src.ui.cli test-connections
  ```
  Should show: "✓ QuickBooks connection successful"

### 3.2 .env Configuration

- [ ] Verify `.env` file exists and has correct settings
- [ ] Check critical settings:
  ```bash
  grep -E "QBO_SANDBOX|QBO_COMPANY_ID|ZIMBRA_HOST" .env
  ```
- [ ] Ensure `.env` has restricted permissions:
  ```bash
  chmod 600 .env
  ```
- [ ] Verify `.qbo_key` and `qbo_tokens.enc` are in `.gitignore`

### 3.3 SSH Access

- [ ] Verify Zimbra host is in known_hosts:
  ```bash
  grep "$(grep ZIMBRA_HOST .env | cut -d= -f2)" ~/.ssh/known_hosts
  ```
- [ ] If not present, add it:
  ```bash
  ssh-keyscan -H your-zimbra-host.com >> ~/.ssh/known_hosts
  ```
- [ ] Test SSH connection:
  ```bash
  python3 -m src.ui.cli test-connections
  ```
  Should show: "✓ Zimbra connection successful" and "Using strict host key verification (secure)"

---

## 4️⃣ First Production Run (Test Mode)

### 4.1 Fetch & Parse Test

- [ ] Run billing WITHOUT creating invoices:
  ```bash
  python3 -m src.ui.cli run-monthly-billing \
    --year 2025 --month $(date -d "last month" +%m) \
    --skip-invoices
  ```
- [ ] Verify output shows:
  - ✓ Reports fetched and parsed
  - ✓ Highwater marks calculated
  - ✓ Excel report generated
  - ✓ No errors in output

### 4.2 Review Excel Report

- [ ] Open generated Excel report:
  ```bash
  # macOS
  open data/billing_report_*.xlsx

  # Linux
  xdg-open data/billing_report_*.xlsx

  # Windows
  start data/billing_report_*.xlsx
  ```
- [ ] Verify:
  - [ ] All domains present
  - [ ] Customer names correct
  - [ ] CoS mappings correct
  - [ ] Prices accurate
  - [ ] Totals reasonable

### 4.3 Reconciliation Check

- [ ] Check for unmapped items:
  ```bash
  python3 -m src.ui.cli reconcile-domains --non-interactive
  python3 -m src.ui.cli reconcile-cos --non-interactive
  ```
- [ ] If unmapped items found, map them interactively:
  ```bash
  python3 -m src.ui.cli reconcile-domains
  python3 -m src.ui.cli reconcile-cos
  ```

---

## 5️⃣ Live (Draft) Invoice Generation

### 5.1 Generate Draft Invoices

- [ ] Create draft invoices (safe, can review in QBO):
  ```bash
  python3 -m src.ui.cli run-monthly-billing \
    --year 2025 --month $(date -d "last month" +%m) \
    --skip-reconciliation
  ```
- [ ] Verify output shows:
  ```
  [4/6] Generating QuickBooks invoices...
        Created N invoices
  ```

### 5.2 Spot-Check QBO Invoices

- [ ] Log into QuickBooks Online
- [ ] Navigate to: **Sales → Invoices**
- [ ] Filter by: **Status: Draft**
- [ ] Randomly inspect 3-5 invoices:
  - [ ] Correct customer
  - [ ] Line items match CoS
  - [ ] Quantities correct
  - [ ] Prices correct
  - [ ] Totals accurate

### 5.3 Idempotency Test (Critical!)

- [ ] Re-run the **same period**:
  ```bash
  python3 -m src.ui.cli run-monthly-billing \
    --year 2025 --month $(date -d "last month" +%m) \
    --skip-reconciliation
  ```
- [ ] Verify logs show:
  ```
  Invoice already exists for customer X for YYYY-MM
  Skipping duplicate creation
  ```
- [ ] Confirm NO new invoices created in QBO
- [ ] **Expected result**: 0 new invoices, all existing invoices detected and skipped

✅ **This confirms idempotency works correctly**

---

## 6️⃣ Automation & Monitoring Setup

### 6.1 Cron/Scheduled Task Setup (Optional)

**macOS/Linux:**
```bash
# Edit crontab
crontab -e

# Add entry (runs 2 AM on 1st of month):
0 2 1 * * cd ~/zimbra-qbo-billing && python3 -m src.ui.cli run-monthly-billing --non-interactive --json-output /var/log/billing/summary.json 2>&1 | logger -t zimbra-billing
```

**Windows Task Scheduler:**
1. Open Task Scheduler → Create Basic Task
2. Name: "Zimbra Monthly Billing"
3. Trigger: Monthly, Day 1, 2:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `-m src.ui.cli run-monthly-billing --non-interactive --json-output C:\billing-logs\summary.json`
   - Start in: `C:\path\to\zimbra-qbo-billing`

### 6.2 Monitoring Setup

- [ ] Create log directory:
  ```bash
  mkdir -p /var/log/billing
  ```
- [ ] Set up log rotation (Linux):
  ```bash
  sudo tee /etc/logrotate.d/zimbra-billing <<EOF
  /var/log/billing/*.log {
    monthly
    rotate 12
    compress
    missingok
  }
  EOF
  ```

### 6.3 Alert Monitoring

Monitor these conditions:
- [ ] Non-zero exit codes from billing runs
- [ ] JSON summary shows `skipped_domains > 0` or `skipped_cos > 0`
- [ ] Invoice creation failures in logs

---

## 7️⃣ Post-Deployment Validation

### 7.1 Database Audit

- [ ] Verify invoice history populated:
  ```bash
  sqlite3 data/billing.db "SELECT COUNT(*) FROM invoice_history WHERE billing_year=2025 AND billing_month=$(date -d 'last month' +%m);"
  ```
- [ ] Check idempotency keys present:
  ```bash
  sqlite3 data/billing.db "SELECT COUNT(*) FROM invoice_history WHERE idempotency_key IS NOT NULL;"
  ```
- [ ] Verify no duplicate keys:
  ```bash
  sqlite3 data/billing.db "SELECT idempotency_key, COUNT(*) FROM invoice_history GROUP BY idempotency_key HAVING COUNT(*) > 1;"
  ```
  Should return no rows.

### 7.2 Security Audit

- [ ] Confirm no plaintext tokens in logs:
  ```bash
  grep -r "refresh_token" data/logs/ 2>/dev/null
  # Should show NO results or only masked tokens
  ```
- [ ] Verify SSH keys have correct permissions:
  ```bash
  ls -la ~/.ssh/id_rsa
  # Should show: -rw------- (600)
  ```
- [ ] Check sensitive files not in git:
  ```bash
  git status --ignored | grep -E "\.qbo_key|qbo_tokens\.enc|\.env"
  # Should show these are ignored
  ```

### 7.3 Backup Verification

- [ ] Verify backups created:
  ```bash
  ls -lh data/billing.db*
  ```
- [ ] Test backup restoration (optional):
  ```bash
  cp data/billing.db data/billing.db.current
  cp data/billing.db.backup data/billing.db.test
  sqlite3 data/billing.db.test "SELECT COUNT(*) FROM customers;"
  rm data/billing.db.test
  ```

---

## 8️⃣ Documentation Check

- [ ] Review updated documentation:
  - [ ] `5_USAGE.md` - Usage guide
  - [ ] `6_PRODUCTION.md` - Production setup
  - [ ] `MIGRATION_GUIDE.md` - Database migrations
  - [ ] `OPERATOR_GUIDE.md` - Operator reference
- [ ] Verify all command examples work
- [ ] Check that security notes are present

---

## 9️⃣ Ongoing Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Token validity check | Monthly | `python3 -m src.ui.cli test-connections` |
| Database backup | Before each run | `cp data/billing.db data/billing.db.$(date +%Y%m%d)` |
| Log review | Weekly | `tail -f data/logs/*.log` |
| Connection test | Monthly | `python3 -m src.ui.cli test-connections` |
| Reconciliation | As needed | `python3 -m src.ui.cli reconcile-domains` |

---

## 🏁 Final Release Confirmation

Once all items above are checked:

- [ ] Tag production deployment:
  ```bash
  git tag -a v1.0.0-prod-deployed -m "Deployed to production $(date +%Y-%m-%d)"
  git push origin v1.0.0-prod-deployed
  ```

- [ ] Document deployment:
  - [ ] Date deployed: ________________
  - [ ] Deployed by: ________________
  - [ ] First billing month: ________________
  - [ ] Invoice count: ________________

- [ ] Create deployment record:
  ```bash
  cat > DEPLOYMENT_RECORD.txt <<EOF
  Version: v1.0.0
  Deployed: $(date)
  Database backup: data/billing.db.$(date +%Y%m%d)
  First run: $(date -d "next month" +%Y-%m)
  Status: ✅ PRODUCTION
  EOF
  ```

---

## ✅ System Status: Production Ready

Your Zimbra-QBO billing system is now:
- ✅ Fully deployed
- ✅ Idempotency verified
- ✅ Security hardened
- ✅ Automated (optional)
- ✅ Monitored
- ✅ Backed up
- ✅ Documented

**Next Steps:**
1. Run first production billing cycle
2. Review draft invoices in QuickBooks
3. Send invoices to customers
4. Monitor first month closely
5. Adjust automation as needed

---

## Support & Troubleshooting

**Documentation:**
- `5_USAGE.md` - Complete usage guide
- `6_PRODUCTION.md` - Production operations
- `OPERATOR_GUIDE.md` - Quick reference for staff
- `MIGRATION_GUIDE.md` - Database migrations

**Common Issues:**
- SSH host key failures → See `3_SETUP_GUIDE.md` section on SSH security
- Token expired → Run `python3 -m src.ui.cli authorize-qbo`
- Unmapped domains → Run `python3 -m src.ui.cli reconcile-domains`

**Emergency Rollback:**
```bash
# Restore previous database
cp data/billing.db.backup data/billing.db

# Verify restoration
python3 -m src.ui.cli test-connections
```

---

**Release Date**: January 2025
**Version**: v1.0.0
**Status**: ✅ Production Ready
