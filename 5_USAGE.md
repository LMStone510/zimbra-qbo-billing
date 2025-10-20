# Usage Guide

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

### Full Automated Run

```bash
python -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

This will:
1. Fetch Zimbra reports via SSH
2. Parse and calculate usage
3. Prompt for any new domains/CoS (interactive reconciliation)
4. Generate draft invoices in QBO
5. Create Excel report

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
```

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

Most commands support:
- `--debug` - Enable debug logging
- `--config PATH` - Use custom config file

## Typical Monthly Process

### First Time Setup (One-time)
1. Install and configure
2. Authorize QBO
3. Sync customers
4. Manually assign all existing domains to customers
5. Map all CoS to QBO items

### Monthly Billing (Recurring)
1. Run billing command for previous month
2. Review and approve any new domain/CoS assignments
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
ssh-copy-id zimbra@mb42.example.com

# Test connection
ssh zimbra@mb42.example.com ls -l /opt/MonthlyUsageReports/
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
