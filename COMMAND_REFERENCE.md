# Command Reference

**Version**: v1.13.0

Complete reference for all billing system commands and their options.

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

## Prerequisites

Before using these commands, ensure you have completed:
1. Application installation and configuration (see `3_APPLICATION_DEPLOYMENT.md`)
2. QuickBooks authorization (`authorize-qbo`)
3. Customer synchronization (`sync-customers`)

For detailed setup instructions, see the numbered deployment guides in the repository.

## Core Commands

### `init-db`
Initialize or reset the database.

**Usage:**
```bash
python -m src.ui.cli init-db
```

**Description:** Creates the database schema and tables. WARNING: Destroys existing data if run on an existing database.

---

### `authorize-qbo`
Authorize QuickBooks Online access via OAuth.

**Usage:**
```bash
python -m src.ui.cli authorize-qbo
```

**Description:** Opens a browser window for OAuth authorization. Must be completed within the authorization window (typically 5 minutes). Tokens are encrypted and stored in `data/qbo_tokens.enc`.

---

### `sync-customers`
Synchronize QuickBooks customers to local database.

**Usage:**
```bash
python -m src.ui.cli sync-customers
```

**Description:** Imports all active customers from QuickBooks Online into the local database. Must be run before first billing cycle and whenever new customers are added in QBO.

---

### `test-connections`
Test all system connections.

**Usage:**
```bash
python -m src.ui.cli test-connections
```

**Description:** Verifies connectivity to:
- Zimbra server (SSH)
- QuickBooks Online (OAuth)
- Local database

---

### `reconcile-domains`
Manually assign domains to customers.

**Usage:**
```bash
python -m src.ui.cli reconcile-domains
```

**Description:** Interactive tool to map Zimbra domains to QuickBooks customers. Shows unmapped domains and prompts for customer assignment.

---

### `reconcile-cos`
Manually map Class of Service to QuickBooks items.

**Usage:**
```bash
python -m src.ui.cli reconcile-cos [--review-all]
```

**Options:**
- `--review-all` - Review all existing CoS mappings, not just unmapped ones

**Description:** Interactive tool to map Zimbra CoS (e.g., "customer-25gb") to QuickBooks service items (e.g., "25GB Mailbox"). System attempts to detect quota sizes to suggest appropriate items.

---

### `generate-report`
Generate Excel billing report without creating invoices.

**Usage:**
```bash
python -m src.ui.cli generate-report --year YYYY --month MM
```

**Required Options:**
- `--year YYYY` - Billing year (e.g., 2025)
- `--month MM` - Billing month (1-12)

**Description:** Fetches Zimbra data, calculates usage, and generates Excel report in `data/billing_report_YYYY_MM_*.xlsx`. Does not create QuickBooks invoices.

---

### `preview-invoices`
Preview invoices without creating them in QuickBooks.

**Usage:**
```bash
python -m src.ui.cli preview-invoices --year YYYY --month MM [--customer-id ID]
```

**Required Options:**
- `--year YYYY` - Billing year
- `--month MM` - Billing month (1-12)

**Optional:**
- `--customer-id ID` - Preview single customer only

**Description:** Shows what invoices would be created, including line items, quantities, and amounts. No data is written to QuickBooks.

---

### `run-monthly-billing`
Run complete monthly billing workflow.

**Usage:**
```bash
python -m src.ui.cli run-monthly-billing [OPTIONS]
```

**Required Options:**
- `--year YYYY` - Billing year (default: current year)
- `--month MM` - Billing month (default: previous month)

**Workflow Control:**
- `--skip-fetch` - Skip fetching Zimbra reports (use cached data)
- `--skip-reconciliation` - Skip domain/CoS reconciliation prompts
- `--skip-invoices` - Skip invoice creation (report only)

**Automation:**
- `--non-interactive` - Run without prompts (safe for cron/schedulers)
- `--json-output PATH` - Write machine-readable summary to file
- `--draft` - Create draft invoices (default: true)

**Global:**
- `--debug` - Enable debug logging
- `--config PATH` - Use custom config file

**Description:** Complete workflow that:
1. Fetches Zimbra usage reports via SSH
2. Parses and calculates monthly high-water marks
3. Reconciles unmapped domains/CoS (interactive or auto-skip)
4. Generates draft invoices in QuickBooks
5. Creates Excel report

**Idempotency:** Safe to re-run. Automatically detects and skips existing invoices for the same billing period.

**Examples:**

```bash
# Interactive run (first time)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10

# Generate report only (no invoices)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices

# Re-run with cached data
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-fetch --skip-reconciliation

# Automated run (cron/scheduler)
python -m src.ui.cli run-monthly-billing --year 2025 --month 10 --non-interactive --json-output /var/log/billing/summary.json
```

---

## Global Options

Available for most commands:

- `--debug` - Enable detailed debug logging
- `--config PATH` - Specify alternate config.json file path

---

## Configuration

The system requires **both** configuration files:

### Required: `.env` file
Contains sensitive credentials (Zimbra SSH, QuickBooks OAuth):

```bash
cp .env.example .env
# Edit with your credentials
```

Required variables:
- `ZIMBRA_HOST` - Zimbra server hostname
- `ZIMBRA_USERNAME` - SSH username
- `ZIMBRA_KEY_FILE` - Path to SSH private key
- `ZIMBRA_REPORT_PATH` - Path to usage reports on Zimbra server
- `QBO_CLIENT_ID` - QuickBooks OAuth client ID
- `QBO_CLIENT_SECRET` - QuickBooks OAuth client secret
- `QBO_REDIRECT_URI` - OAuth redirect URI
- `QBO_COMPANY_ID` - QuickBooks company ID
- `QBO_SANDBOX` - `true` for sandbox, `false` for production
- `DATABASE_PATH` - Path to SQLite database

### Optional: `data/config.json` file
Contains exclusion patterns and other settings:

```bash
cp data/config.json.example data/config.json
# Edit exclusions as needed
```

Used for:
- Domain exclusion patterns (wildcard matching)
- CoS exclusion patterns
- Logging configuration

**Configuration Priority:** Environment variables (`.env`) override `config.json` which overrides defaults.

---

## JSON Output Format

When using `--json-output`, the system generates a machine-readable summary:

```json
{
  "run_metadata": {
    "timestamp": "2025-10-01T02:00:00",
    "billing_period": {
      "year": 2025,
      "month": 10
    }
  },
  "invoices": {
    "total_count": 87,
    "success_count": 87,
    "failed_count": 0,
    "total_amount": 12450.00
  },
  "reconciliation": {
    "skipped_domains": 0,
    "skipped_cos": 0,
    "unmapped_items": []
  },
  "status": "success"
}
```

**Use Cases:**
- CI/CD pipeline integration
- Monitoring and alerting
- Automated result parsing
- Historical tracking

---

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Connection error (Zimbra or QuickBooks)
- `4` - Authorization error

---

## Additional Resources

- **5_OPERATOR_GUIDE.md** - Monthly billing workflow and procedures
- **3_APPLICATION_DEPLOYMENT.md** - Initial setup and configuration
- **PROJECT_REFERENCE.md** - Technical architecture and features
