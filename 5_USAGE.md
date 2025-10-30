# Usage Guide

**Version**: v1.13.0

## Command Syntax

This guide uses `python -m src.ui.cli` for all commands, which works on all platforms without additional setup.

**Alternative**: After installing with `pip install -e .`, you can also use:
```bash
zimbra-billing <command>
```

For example:
```bash
# These are equivalent:
python -m src.ui.cli run-monthly-billing --year 2025 --month 10
zimbra-billing run-monthly-billing --year 2025 --month 10
```

All examples below use `python -m src.ui.cli` for consistency.

## Initial Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Application

Copy the example configuration:

```bash
cp data/config.json.example data/config.json
```

Edit `data/config.json` with your settings:
- Zimbra SSH credentials and server details
- QuickBooks Online API credentials
- Exclusion patterns

Or use environment variables (see `.env.example`):

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Initialize Database

```bash
python -m src.ui.cli init-db
```

### 4. Authorize QuickBooks Online

```bash
python -m src.ui.cli authorize-qbo
```

This will open your browser for OAuth authorization.

### 5. Sync Customers

```bash
python -m src.ui.cli sync-customers
```

This imports your QBO customers into the local database.

### 6. Test Connections

```bash
python -m src.ui.cli test-connections
```

## Monthly Billing Workflow

### Full Automated Run (Interactive)

```bash
python -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

This will:
1. Fetch Zimbra reports via SSH
2. Parse and calculate usage
3. Prompt for any new domains/CoS (interactive reconciliation)
4. Generate draft invoices in QBO
5. Create Excel report

### Automated Run (Non-Interactive for Cron/Scheduling)

```bash
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --non-interactive
```

Perfect for scheduled/automated runs:
- Skips all interactive prompts
- Uses safe defaults for unmapped items
- Reports what needs manual attention
- Prevents duplicate invoices with idempotency
- Safe to re-run the same period

### Automated Run with JSON Output (CI/CD Pipelines)

For automation and monitoring, use the `--json-output` flag to generate a machine-readable summary:

```bash
python -m src.ui.cli run-monthly-billing \
  --year 2025 --month 10 \
  --non-interactive \
  --json-output /var/log/billing/2025-10-summary.json
```

**JSON Output Format:**
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

**Use Cases:**
- Monitor billing runs from CI/CD pipelines
- Parse results in automated workflows
- Track invoice counts and amounts over time
- Alert on failures or skipped items
- Integrate with monitoring systems (Datadog, Prometheus, etc.)

### Step-by-Step Workflow

If you prefer more control:

#### 1. Generate Report Only

```bash
python -m src.ui.cli generate-report --year 2025 --month 10
```

#### 2. Preview Invoices

```bash
# Preview all invoices
python -m src.ui.cli preview-invoices --year 2025 --month 10

# Preview specific customer
python -m src.ui.cli preview-invoices --year 2025 --month 10 --customer-id 5
```

#### 3. Reconcile Domains

```bash
python -m src.ui.cli reconcile-domains
```

#### 4. Reconcile CoS

```bash
python -m src.ui.cli reconcile-cos
```

#### 5. Run Billing (Skip Steps)

```bash
# Skip fetching (use existing data)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-fetch

# Skip reconciliation
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-reconciliation

# Skip invoice generation (report only)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices

# Non-interactive mode (for automation)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --non-interactive

# With JSON output for machine processing
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --json-output summary.json
```

### Safe Re-runs and Idempotency

**The system now prevents duplicate invoices automatically.**

You can safely re-run the same billing period multiple times:

```bash
# First run - creates invoices
python -m src.ui.cli run-monthly-billing --year 2025 --month 10

# Second run (same period) - skips existing invoices
python -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

The system will:
- Detect invoices already created for that period
- Skip creating duplicates
- Log which invoices were skipped
- Process only new/missing invoices

This is safe for:
- Recovering from partial failures
- Re-running after fixing data issues
- Testing invoice generation multiple times

## Command Reference

### Core Commands

- `run-monthly-billing` - Run complete monthly billing workflow
- `generate-report` - Generate Excel report only
- `preview-invoices` - Preview invoices without creating
- `reconcile-domains` - Manually assign domains to customers
- `reconcile-cos` - Manually map CoS to QBO items
- `sync-customers` - Sync QBO customers to database
- `authorize-qbo` - Authorize QBO access
- `test-connections` - Test Zimbra and QBO connections
- `init-db` - Initialize/reset database

### Command Options

**Global Options** (most commands):
- `--debug` - Enable debug logging
- `--config PATH` - Use custom config file

**run-monthly-billing Options**:
- `--year YEAR` - Billing year (default: current year)
- `--month MONTH` - Billing month (default: last month)
- `--skip-fetch` - Skip fetching reports (use existing data)
- `--skip-reconciliation` - Skip reconciliation prompts
- `--skip-invoices` - Skip invoice generation (report only)
- `--draft` - Create draft invoices (default: true)
- `--non-interactive` - Run without prompts (for automation)
- `--json-output PATH` - Write JSON summary to file

## Typical Monthly Process

### First Time Setup (One-time)
1. Install and configure
2. Authorize QBO
3. Sync customers
4. Manually assign all existing domains to customers
5. Map all CoS to QBO items

### Monthly Billing (Recurring)

**Interactive Mode** (first few months):
1. Run billing command for previous month
2. Review and approve any new domain/CoS assignments
3. Verify draft invoices in QuickBooks
4. Send invoices to customers

**Automated Mode** (once stable):
1. Set up cron job or scheduled task
2. Run with `--non-interactive` flag
3. System auto-processes known items
4. Check JSON summary for any issues
5. Manually reconcile only new items

### Scheduled/Automated Billing

Once your domain and CoS mappings are stable, you can automate monthly billing:

#### Linux/macOS Cron Example

```bash
# Edit crontab
crontab -e

# Run on 1st of each month at 2 AM
0 2 1 * * cd ~/zimbra-qbo-billing && python3 -m src.ui.cli run-monthly-billing --non-interactive --json-output /var/log/billing/$(date +\%Y-\%m).json 2>&1 | logger -t zimbra-billing
```

#### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Monthly (1st day, 2:00 AM)
4. Action: Start a program
   - Program: `python`
   - Arguments: `-m src.ui.cli run-monthly-billing --non-interactive --json-output C:\billing-logs\summary.json`
   - Start in: `C:\zimbra-qbo-billing`

#### Monitoring Automated Runs

Check the JSON output file:
```bash
# View summary
cat /var/log/billing/2025-10.json | jq '.status'

# Check for failures
cat /var/log/billing/2025-10.json | jq '.failures'

# See skipped items
cat /var/log/billing/2025-10.json | jq '.reconciliation.items'
```
3. Review generated invoices in QBO (they're drafts)
4. Review Excel report
5. Send invoices from QBO

## Tips

### Testing
- Use `--skip-invoices` to generate reports without creating invoices
- Use `preview-invoices` to see what would be billed
- Invoices are created as drafts by default for review

### Automation
- Set up a cron job to run billing on the 1st of each month
- Use `--skip-reconciliation` if you want fully automated runs
  (new items will be skipped until manually reconciled)

### Troubleshooting
- Check logs in `data/logs/`
- Use `--debug` flag for verbose output
- Run `test-connections` to verify connectivity
- Make sure exclusion patterns are configured correctly

## Configuration Tips

### Exclusion Patterns

Add patterns to `config.json` to exclude domains/CoS from billing:

```json
{
  "exclusions": {
    "domains": [
      "*.test",
      "*-archive",
      "internal.company.com"
    ],
    "cos_patterns": [
      "*-test",
      "*-trial",
      "internal-*"
    ]
  }
}
```

Patterns use shell-style wildcards:
- `*` matches any characters
- `?` matches single character
- Case-insensitive matching

### SSH Key Setup

For passwordless Zimbra access:

```bash
# Generate key if needed
ssh-keygen -t rsa -b 4096

# Copy to Zimbra server
ssh-copy-id zimbra@your-zimbra-server.com

# Test connection
ssh zimbra@your-zimbra-server.com ls -l /opt/MonthlyUsageReports/
```

## Database Maintenance

### Backup Database

The database is backed up automatically before major operations, but you can also:

```bash
cp data/billing.db data/billing.db.backup-$(date +%Y%m%d)
```

### Reset Database

If you need to start fresh:

```bash
python -m src.ui.cli init-db
```

WARNING: This deletes all data!
