# Quick Start Guide

**Current Status**: ✅ Fully configured and tested with QuickBooks Sandbox

## Already Set Up

The application is already installed and configured! You can:
- ✅ Run billing for March 2025 data
- ✅ Generate reports
- ✅ Create draft invoices in sandbox

**To switch to Production QuickBooks**, see **3_SETUP_GUIDE.md** or **6_PRODUCTION.md**

## Quick Reference

### Testing with Existing Data

```bash
cd ~/zimbra-qbo-billing

# Generate report only (no invoices)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-invoices --skip-fetch

# Full run with draft invoices
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation
```

### For New Installations

### 1. Install (1 min)
```bash
cd ~/zimbra-qbo-billing
pip3 install -e .
```

### 2. Configure (2 min)

The `.env` file is already configured with:
- Zimbra SSH connection details
- QuickBooks OAuth credentials
- Sandbox settings

**For production**, see **PRODUCTION.md**

### 3. Initialize (2 min)
```bash
# Create database
python3 -m src.ui.cli init-db

# Authorize QBO (opens browser)
python3 -m src.ui.cli authorize-qbo

# Import customers
python3 -m src.ui.cli sync-customers

# Test connections
python3 -m src.ui.cli test-connections
```

## First Billing Run

### Option A: Interactive (Recommended First Time)
```bash
# Run full workflow with prompts for new items
python -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

This will:
1. Fetch reports from Zimbra
2. Calculate usage
3. **Prompt you** to assign any new domains to customers
4. **Prompt you** to map any new CoS to QBO items
5. Generate draft invoices
6. Create Excel report

### Option B: Preview Only
```bash
# Generate report without invoices
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices

# Preview what invoices would be created
python -m src.ui.cli preview-invoices --year 2025 --month 10
```

## Common Commands

```bash
# Full monthly billing
python -m src.ui.cli run-monthly-billing --year 2025 --month 10

# Just the report
python -m src.ui.cli generate-report --year 2025 --month 10

# Preview invoices
python -m src.ui.cli preview-invoices --year 2025 --month 10

# Manual reconciliation
python -m src.ui.cli reconcile-domains
python -m src.ui.cli reconcile-cos

# Sync customers from QBO
python -m src.ui.cli sync-customers

# Test connections
python -m src.ui.cli test-connections
```

## File Locations

- **Config**: `data/config.json`
- **Database**: `data/billing.db`
- **Reports**: `data/billing_report_YYYY_MM.xlsx`
- **Logs**: `data/logs/`
- **Tokens**: `data/qbo_tokens.enc` (encrypted)

## Quick Troubleshooting

### Can't connect to Zimbra
```bash
# Test SSH manually
ssh zimbra@YOUR_HOST ls /opt/MonthlyUsageReports/

# Check config
cat data/config.json | grep zimbra
```

### QBO authorization failed
```bash
# Re-authorize
python -m src.ui.cli authorize-qbo

# Check credentials in config.json
```

### Need debug info
```bash
# Run with debug logging
python -m src.ui.cli --debug run-monthly-billing --year 2025 --month 10

# Check logs
tail -f data/logs/*.log
```

## Typical Monthly Workflow

**Day 1 of each month:**

```bash
# Run billing for previous month
python -m src.ui.cli run-monthly-billing

# Review Excel report (use command for your OS)
open data/billing_report_2025_10.xlsx        # macOS
xdg-open data/billing_report_2025_10.xlsx    # Linux
start data/billing_report_2025_10.xlsx       # Windows

# Review draft invoices in QBO web interface
# https://app.qbo.intuit.com/app/invoices

# Send invoices from QBO when ready
```

## Automation Setup

**macOS/Linux** - Add to crontab for automatic monthly runs:

```bash
# Run at 6am on the 1st of each month
0 6 1 * * cd ~/zimbra-qbo-billing && /usr/bin/python3 -m src.ui.cli run-monthly-billing --skip-reconciliation >> data/logs/cron.log 2>&1
```

**Windows** - Use Task Scheduler:
1. Open Task Scheduler → Create Basic Task
2. Trigger: Monthly, Day 1, 6:00 AM
3. Action: Start a program
   - Program: `python`
   - Arguments: `-m src.ui.cli run-monthly-billing --skip-reconciliation`
   - Start in: `C:\path\to\zimbra-qbo-billing`

Note: Use `--skip-reconciliation` for unattended runs. New domains/CoS will be skipped until manually reconciled.

## Getting Help

```bash
# Command help
python -m src.ui.cli --help
python -m src.ui.cli run-monthly-billing --help

# Detailed docs
cat 5_USAGE.md
cat 7_PROJECT_SUMMARY.md
```

## Important Notes

1. **Invoices are drafts** - Always review before sending
2. **Backup before first run** - `cp data/billing.db data/billing.db.backup`
3. **Test with --skip-invoices first** - Generate reports without creating invoices
4. **QBO tokens expire** - Re-authorize if needed (automatic refresh for 101 days)
5. **Exclusions** - Configure patterns to skip test/archive domains

## Next Steps After First Run

1. Review generated Excel report
2. Check draft invoices in QBO
3. Adjust exclusion patterns if needed
4. Set up monthly automation
5. Consider backing up database regularly

---

**Need more help?** See `5_USAGE.md` for detailed documentation or `3_SETUP_GUIDE.md` for the complete setup process.
