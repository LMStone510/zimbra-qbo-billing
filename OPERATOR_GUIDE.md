# Zimbra-QBO Billing Operator Quick Reference

**Version**: v1.0.0
**Audience**: Billing staff and operations team
**Purpose**: Simple, step-by-step guide for monthly billing operations

---

## 📋 Quick Facts

- **What it does**: Automatically fetches Zimbra usage and creates QuickBooks invoices
- **How often**: Run once per month (1st or 2nd of the month)
- **Invoice type**: Creates **DRAFT** invoices only - you review before sending
- **Safety**: Can safely re-run - won't create duplicates
- **Time required**: 5-10 minutes (automated parts run unattended)

---

## 🎯 Before You Start

### Check These First

```bash
# 1. Verify you're in the right directory
cd ~/zimbra-qbo-billing

# 2. Test connections (should see green checkmarks)
python3 -m src.ui.cli test-connections
```

**Expected output:**
```
✓ Zimbra connection successful
✓ QuickBooks connection successful
```

If you see any ❌ errors, see **Troubleshooting** section below.

---

## 📅 Monthly Billing Process

### Step 1: Backup Database (30 seconds)

Always backup before running:

```bash
# Creates backup with today's date
cp data/billing.db data/billing.db.$(date +%Y%m%d)
```

**Verification:**
```bash
ls -lh data/billing.db*
# Should show original and backup file
```

---

### Step 2: Generate Report Only (First Time)

Test first without creating invoices:

```bash
# Replace YYYY and MM with year and month to bill
python3 -m src.ui.cli run-monthly-billing \
  --year 2025 --month 10 \
  --skip-invoices
```

**What happens:**
1. Fetches reports from Zimbra (via SSH)
2. Calculates usage for each domain
3. Generates Excel report
4. Shows billing summary
5. **Does NOT create invoices**

**Time:** ~2-5 minutes

---

### Step 3: Review Excel Report

Open the report:

```bash
# macOS
open data/billing_report_2025_10_*.xlsx

# Linux
xdg-open data/billing_report_2025_10_*.xlsx

# Windows
start data\billing_report_2025_10_*.xlsx
```

**Check:**
- [ ] All customers present
- [ ] Domain assignments correct
- [ ] Prices accurate
- [ ] Totals reasonable

**If something looks wrong**, see **Fixing Issues** section.

---

### Step 4: Create Draft Invoices

When report looks good, create invoices:

```bash
python3 -m src.ui.cli run-monthly-billing \
  --year 2025 --month 10 \
  --skip-reconciliation
```

**What happens:**
1. Skips fetching (uses existing data)
2. Creates **DRAFT** invoices in QuickBooks
3. Shows summary of invoices created

**Output example:**
```
[4/6] Generating QuickBooks invoices...
      Created 87 invoices

Billing Summary:
Billing Period: 2025-10
Invoices Created: 87
Total Amount: $12,450.00
```

**Time:** ~5-10 minutes

---

### Step 5: Review Draft Invoices in QuickBooks

1. Log into QuickBooks Online: https://qbo.intuit.com
2. Go to **Sales** → **Invoices**
3. Filter by: **Status = Draft**
4. Review a few invoices (at least 3-5):
   - Correct customer?
   - Line items correct?
   - Prices accurate?
   - Totals match Excel report?

**If issues found**, see **Fixing Issues** section.

---

### Step 6: Send Invoices

Once you've verified drafts are correct:

**Option A - Send All** (in QuickBooks):
1. Select all draft invoices
2. Click **Batch Actions** → **Send Invoices**
3. Customize email template if needed
4. Click **Send**

**Option B - Send Individually** (recommended first time):
1. Open each invoice
2. Review once more
3. Click **Save and Send**

---

## 🔄 Automated Mode (Once Comfortable)

After a few months of manual runs, you can automate:

```bash
python3 -m src.ui.cli run-monthly-billing \
  --non-interactive \
  --json-output /var/log/billing/summary.json
```

**Benefits:**
- Runs without prompts (safe for cron/scheduler)
- Creates JSON summary for monitoring
- Skips unmapped items (reports them)
- Still creates DRAFT invoices only

**Cron Example** (runs automatically on 1st of month at 2 AM):
```bash
0 2 1 * * cd ~/zimbra-qbo-billing && python3 -m src.ui.cli run-monthly-billing --non-interactive --json-output /var/log/billing/summary.json
```

---

## 🛠️ Fixing Issues

### Unmapped Domains

**Symptom:** Report shows domains not assigned to customers

**Fix:**
```bash
# Interactive assignment
python3 -m src.ui.cli reconcile-domains

# Follow prompts to assign each domain to a customer
```

---

### Unmapped CoS (Class of Service)

**Symptom:** Some mailbox types not mapped to QuickBooks items

**Fix:**
```bash
# Interactive mapping
python3 -m src.ui.cli reconcile-cos

# Follow prompts to map each CoS to a QuickBooks item
```

---

### Wrong Prices

**Issue:** Prices in invoices don't match your rates

**Fix:**
1. Update prices in **QuickBooks** (Sales → Products and Services)
2. Re-map CoS to pick up new prices:
   ```bash
   python3 -m src.ui.cli reconcile-cos
   ```
3. Re-run billing for that month (safe - won't duplicate)

---

### Connection Failures

**SSH Error** (can't reach Zimbra):
```bash
# Add Zimbra server to known hosts
ssh-keyscan -H your-zimbra-host.com >> ~/.ssh/known_hosts

# Test again
python3 -m src.ui.cli test-connections
```

**QuickBooks Error** (token expired):
```bash
# Re-authorize (opens browser)
python3 -m src.ui.cli authorize-qbo
```

---

## 🔒 Safety Features

### Can I Re-Run Safely?

**YES!** The system prevents duplicate invoices automatically.

```bash
# Running the same month twice is SAFE:
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10  # ← Safe!
```

**What happens:**
- First run: Creates invoices
- Second run: Detects existing invoices, skips them
- Log shows: "Invoice already exists... Skipping duplicate"

**When to re-run:**
- If partial failure occurred
- After fixing mapping issues
- To add newly mapped domains

---

## 📊 Understanding Reports

### Excel Report

**Location:** `data/billing_report_YYYY_MM_*.xlsx`

**Sheets:**
1. **Summary** - Overview by customer
2. **Details** - Line-by-line billing
3. **Usage** - Raw usage data

### JSON Summary (Automated Mode)

**Location:** Specified with `--json-output` flag

**Example:**
```json
{
  "run_metadata": {
    "timestamp": "2025-10-01T02:00:00",
    "billing_period": {"year": 2025, "month": 10}
  },
  "invoices": {
    "total_count": 87,
    "success_count": 87,
    "failed_count": 0,
    "total_amount": 12450.00
  },
  "reconciliation": {
    "skipped_domains": 0,
    "skipped_cos": 0
  },
  "status": "success"
}
```

**What to check:**
- `failed_count` should be 0
- `skipped_domains` should be 0 (or map them)
- `status` should be "success"

---

## 📅 Monthly Checklist

Use this each month:

- [ ] **Day 1**: Backup database
- [ ] **Day 1**: Run with `--skip-invoices` (report only)
- [ ] **Day 1**: Review Excel report
- [ ] **Day 1-2**: Fix any unmapped domains/CoS
- [ ] **Day 2**: Create draft invoices
- [ ] **Day 2**: Review drafts in QuickBooks
- [ ] **Day 2-3**: Send invoices to customers
- [ ] **Day 7**: Verify backups stored safely

---

## 🆘 Common Questions

### Q: What if I accidentally run twice?

**A:** No problem! The system detects existing invoices and skips them. No duplicates will be created.

---

### Q: What if prices changed mid-month?

**A:** Update prices in QuickBooks, re-map CoS, then re-run. The system will skip already-created invoices and use new prices for any new ones.

---

### Q: Can I bill for just one customer?

**A:** Not directly via CLI, but you can:
1. Run full billing
2. Delete unwanted draft invoices in QuickBooks
3. Keep only the ones you want

---

### Q: What if Zimbra was down during the month?

**A:** The system uses "high-water mark" - it bills for the maximum simultaneous users seen at any point. A few hours of downtime won't affect billing.

---

### Q: How far back can I bill?

**A:** As long as you have Zimbra reports for that month. Reports are typically kept for 12 months.

---

## 📞 Getting Help

**Check These First:**
1. Review error messages in terminal
2. Check logs: `tail -f data/logs/*.log`
3. Review this guide
4. Check `5_USAGE.md` for detailed commands

**Documentation:**
- `5_USAGE.md` - Complete usage guide
- `6_PRODUCTION.md` - Production setup details
- `3_SETUP_GUIDE.md` - Initial setup
- `MIGRATION_GUIDE.md` - Database changes

**Emergency Contact:**
- IT Support: [Your contact info]
- System Admin: [Your contact info]

---

## 🔐 Security Notes

- **Tokens encrypted**: OAuth tokens are encrypted and masked in logs
- **SSH secure**: Uses verified host keys (no automatic trust)
- **Invoices are drafts**: You must manually review and send
- **Backups important**: Always backup before running
- **Safe re-runs**: Duplicate invoice prevention built-in

---

## ✅ Quick Command Reference

```bash
# Test everything works
python3 -m src.ui.cli test-connections

# Backup database
cp data/billing.db data/billing.db.$(date +%Y%m%d)

# Generate report only (no invoices)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices

# Create draft invoices
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-reconciliation

# Fix unmapped domains
python3 -m src.ui.cli reconcile-domains

# Fix unmapped CoS
python3 -m src.ui.cli reconcile-cos

# Re-authorize QuickBooks
python3 -m src.ui.cli authorize-qbo

# See all commands
python3 -m src.ui.cli --help
```

---

**Remember**:
- ✅ Invoices are **DRAFTS** - you control when they send
- ✅ Re-running is **SAFE** - no duplicates created
- ✅ Always **BACKUP** before running
- ✅ **REVIEW** drafts in QuickBooks before sending

---

**Version**: v1.0.0
**Last Updated**: January 2025
**System Status**: ✅ Production Ready
