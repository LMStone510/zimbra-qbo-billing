# Zimbra-to-QuickBooks Billing Automation - Project Reference

**Version**: v1.13.0

**Status**: ✅ Fully operational, tested with QuickBooks Sandbox and used in production at Mission Critical Email

**Platform Support**: macOS | Linux | Windows

> 👋 **New here?** Start with **README.md** for a friendly introduction!

Automated monthly billing system that:
- Fetches Zimbra email usage reports via SSH/SCP
- Calculates monthly high-water marks per domain/CoS
- Maps domains to QuickBooks Online customers
- Generates draft invoices in QBO
- Produces Excel summary reports

---

## Table of Contents

1. [Implementation Status](#implementation-status)
2. [Platform Compatibility](#platform-compatibility)
3. [Quick Start](#quick-start)
4. [Project Structure](#project-structure)
5. [Implemented Features](#implemented-features)
6. [Key Capabilities](#key-capabilities)
7. [Database Schema](#database-schema)
8. [Configuration](#configuration)
9. [Common Commands](#common-commands)
10. [Documentation Guide](#documentation-guide)
11. [Security](#security)
12. [Error Handling](#error-handling)
13. [Switching to Production](#switching-to-production)
14. [Important Notes](#important-notes)
15. [License](#license)

---

## Implementation Status

✅ **All 6 phases implemented and tested**
✅ **Successfully tested with QuickBooks Sandbox**
✅ **Currently in production at Mission Critical Email**

### Test Results (March 2025)
- Fetched 6 weekly reports from Zimbra
- Parsed 87 domains with usage data
- Calculated 151 highwater marks
- Mapped 85 domains to customers
- Mapped 31 CoS types to QuickBooks items
- Generated 69 billable line items
- Total billing: **$3,210.00**
- Excel report generated successfully

### Production Status

✅ **Database cleaned and ready for production**:
- All sandbox test data has been removed
- All customer mappings cleared
- All CoS mappings cleared
- Ready for fresh production setup

📋 **Previously Tested Successfully**:
- Fetched reports from Zimbra via SSH
- Parsed 87 domains with usage data
- Interactive reconciliation workflow verified
- Invoice generation tested
- Excel reports generated with correct calculations

---

## Platform Compatibility

This application is fully cross-platform:
- ✅ **macOS** (10.15+) - Developed and tested
- ✅ **Linux** (Ubuntu 20.04+, Debian, RHEL, etc.)
- ✅ **Windows** (10/11 with Python 3.8+)

**Requirements**: Python 3.8+, pip3, SSH client, SSH keys for Zimbra access

---

## Quick Start

### Prerequisites

**⚠️ IMPORTANT: Set up Zimbra server FIRST!**

**On Zimbra Server** (one-time setup):
1. Install the usage report script
2. Configure cron to generate weekly reports
3. See **1_ZIMBRA_SERVER_SETUP.md** for complete instructions (DO THIS FIRST!)

**On Billing Server**:

### Installation
```bash
git clone https://github.com/LMStone510/zimbra-qbo-billing.git
cd zimbra-qbo-billing
pip3 install -e .
```

### Initial Setup
```bash
# Initialize database
python3 -m src.ui.cli init-db

# Authorize QuickBooks (opens browser)
python3 -m src.ui.cli authorize-qbo

# Import customers from QBO
python3 -m src.ui.cli sync-customers

# Test connections
python3 -m src.ui.cli test-connections
```

### Run Monthly Billing
```bash
# Full interactive run with reconciliation
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3

# Generate report without creating invoices (recommended first time)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-invoices
```

---

## Project Structure

```
invoicing/
├── src/                              # Source code
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── main.py                       # Main application entry
│   ├── database/                     # Database layer
│   │   ├── __init__.py
│   │   ├── models.py                 # SQLAlchemy models
│   │   ├── queries.py                # Database query functions
│   │   └── migrations.py             # Database migrations
│   ├── zimbra/                       # Zimbra integration
│   │   ├── __init__.py
│   │   ├── fetcher.py                # SSH/SCP report fetching
│   │   ├── parser.py                 # CSV parsing and validation
│   │   └── calculator.py             # High-water mark calculations
│   ├── qbo/                          # QuickBooks Online integration
│   │   ├── __init__.py
│   │   ├── auth.py                   # OAuth 2.0 authentication
│   │   ├── client.py                 # QBO API client wrapper
│   │   ├── errors.py                 # QBO error handling
│   │   └── invoice.py                # Invoice creation logic
│   ├── reconciliation/               # Domain/CoS reconciliation
│   │   ├── __init__.py
│   │   ├── detector.py               # Change detection
│   │   ├── mapper.py                 # Mapping management
│   │   └── prompter.py               # Interactive prompts
│   ├── reporting/                    # Report generation
│   │   ├── __init__.py
│   │   └── excel.py                  # Excel report generation
│   └── ui/                           # User interface
│       ├── __init__.py
│       └── cli.py                    # Command-line interface
├── data/                             # Application data
│   ├── billing.db                    # SQLite database
│   ├── config.json                   # JSON configuration (optional)
│   ├── config.json.example           # Example configuration
│   ├── .qbo_key                      # OAuth encryption key
│   ├── .qbo_key.example              # Example key file
│   ├── qbo_tokens.enc                # Encrypted OAuth tokens
│   ├── logs/                         # Application logs
│   └── billing_report_*.xlsx         # Generated Excel reports
├── scripts/                          # Zimbra and utility scripts
│   ├── MonthlyBillingByDomain-v6.sh  # Usage report script
│   ├── compare_june_invoices.sh      # Invoice comparison tool
│   ├── prepare_june_retest.sh        # Test preparation script
│   └── README.md                     # Script documentation
├── tests/                            # Test suite
│   ├── test_parser.py                # Parser unit tests
│   ├── test_money_precision.py       # Money precision tests
│   ├── test_qbo_errors.py            # QBO error handling tests
│   ├── test_query_escaping.py        # SQL query escaping tests
│   ├── generate_sample_data.py       # Test data generator
│   └── sample_data/                  # Sample Zimbra reports
├── .env                              # Environment configuration (primary)
├── .env.example                      # Example environment file
├── setup.py                          # Python package setup
├── requirements.txt                  # Python dependencies
├── LICENSE                           # MIT License
├── README.md                         # Project overview
├── 1_QBO_DEVELOPER_SETUP.md          # QuickBooks Developer setup
├── 2_ZIMBRA_SERVER_SETUP.md          # Zimbra server setup guide
├── 3_APPLICATION_DEPLOYMENT.md       # Application deployment
├── 4_PRODUCTION_DEPLOYMENT.md        # Production deployment
├── 5_OPERATOR_GUIDE.md               # Operational procedures
├── COMMAND_REFERENCE.md              # Command reference
├── PROJECT_REFERENCE.md              # This file - technical reference
└── 99_CODE_AUDIT.md                  # Code audit report
```

---

## Implemented Features

### Phase 1: Foundation ✅
- **Configuration Management** - Supports config file, environment variables, and defaults
- **Database Models** - Complete SQLAlchemy schema with 11 tables
- **Database Migrations** - Initialization, backup, and default data loading
- **Query Helpers** - Comprehensive database query utilities

### Phase 2: Zimbra Integration ✅
- **SSH/SCP Fetcher** - Connects to Zimbra server and downloads reports
- **Report Parser** - Parses weekly usage reports, extracts domains/CoS/counts
- **High-water Calculator** - Computes monthly maximum usage per domain/CoS
- **Exclusion Support** - Filter out non-billable items

### Phase 3: Reconciliation Engine ✅
- **Change Detector** - Identifies new domains, missing domains, new CoS
- **Interactive Prompter** - User-friendly CLI prompts for decisions
- **Mapping Manager** - Maintains domain→customer and CoS→QBO item mappings
- **History Tracking** - Logs all changes and user decisions

### Phase 4: QuickBooks Online ✅
- **OAuth2 Authentication** - Secure token storage with encryption
- **QBO API Client** - Wrapper for customer, item, and invoice operations
- **Invoice Generator** - Creates invoices from usage data
- **Rate Limiting** - Prevents API throttling

### Phase 5: Reporting & UI ✅
- **Excel Reports** - Multi-sheet reports with summary, details, and breakdowns
- **CLI Interface** - 10+ commands for all operations
- **Progress Indicators** - Clear feedback during operations
- **Error Handling** - Comprehensive error messages

### Phase 6: Main Orchestration ✅
- **Monthly Workflow** - Complete end-to-end automation
- **Step-by-Step Process** - Fetch → Parse → Reconcile → Invoice → Report
- **Flexible Execution** - Skip steps as needed
- **Summary Display** - Clear billing summary

---

## Key Capabilities

1. **Automated Report Fetching** - SSH into Zimbra server and download reports
2. **Intelligent Parsing** - Extract domains, CoS, and account counts
3. **High-water Billing** - Calculate maximum monthly usage per domain/CoS
4. **Smart Reconciliation** - Detect and handle new/missing domains and CoS
5. **QBO Integration** - Create draft invoices with proper line items
6. **Excel Reporting** - Professional multi-sheet billing reports
7. **Audit Trail** - Complete change log and history tracking
8. **Exclusion Patterns** - Flexible filtering of non-billable items

---

## Database Schema

11 tables with comprehensive relationships:
- `customers` - QBO customer records
- `domains` - Domain to customer mappings
- `exclusions` - Exclusion patterns
- `cos_mappings` - CoS to QBO item mappings with pricing
- `usage_data` - Raw weekly usage data
- `monthly_highwater` - Calculated monthly maximums
- `invoice_history` - Generated invoice tracking
- `customer_settings` - Per-customer preferences
- `domain_history` - Domain change history
- `cos_discovery` - New CoS tracking
- `change_log` - Audit log

---

## Configuration

The application uses `.env` file for configuration (already configured):

```bash
# Zimbra Configuration
ZIMBRA_HOST=your-zimbra-server.com
ZIMBRA_USERNAME=ubuntu
ZIMBRA_KEY_FILE=~/.ssh/id_rsa
ZIMBRA_REPORT_PATH=/opt/MonthlyUsageReports

# QuickBooks Online Configuration
QBO_CLIENT_ID=<your-client-id>
QBO_CLIENT_SECRET=<your-client-secret>
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_COMPANY_ID=<your-company-id>
QBO_SANDBOX=true  # Set to false for production

# Database Configuration
DATABASE_PATH=data/billing.db
```

---

## Common Commands

### Main Commands

```bash
# Monthly billing (full workflow)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3

# Generate report only
python3 -m src.ui.cli generate-report --year 2025 --month 3

# Preview invoices without creating them
python3 -m src.ui.cli preview-invoices --year 2025 --month 3

# Manual reconciliation
python3 -m src.ui.cli reconcile-domains
python3 -m src.ui.cli reconcile-cos

# Test connections
python3 -m src.ui.cli test-connections

# Sync customers from QBO
python3 -m src.ui.cli sync-customers
```

### Setup Commands

```bash
# Initialize database
python3 -m src.ui.cli init-db

# Authorize QuickBooks (opens browser)
python3 -m src.ui.cli authorize-qbo

# Import customers from QBO
python3 -m src.ui.cli sync-customers

# Test all connections
python3 -m src.ui.cli test-connections
```

---

## Documentation Guide

Follow the 5-step journey:

1. **README.md** - 👋 **Start here!** Overview and journey map
2. **1_QBO_DEVELOPER_SETUP.md** - Step 1: QuickBooks Developer setup
3. **2_ZIMBRA_SERVER_SETUP.md** - Step 2: Zimbra server setup
4. **3_APPLICATION_DEPLOYMENT.md** - Step 3: Application deployment and sandbox testing
5. **4_PRODUCTION_DEPLOYMENT.md** - Step 4: Production deployment
6. **5_OPERATOR_GUIDE.md** - Step 5: Monthly operations

**Reference Documents:**
- **COMMAND_REFERENCE.md** - Detailed command reference
- **PROJECT_REFERENCE.md** - This file - Technical architecture
- **99_CODE_AUDIT.md** - Code quality audit report

---

## Security

- **OAuth2 Token Encryption** - Tokens encrypted at rest using Fernet encryption
- **SSH Key Authentication** - Passwordless access to Zimbra server
- **Restrictive Permissions** - Sensitive files have secure permissions
- **No Hardcoded Credentials** - All credentials in environment/config files
- **Masked Logging** - Credentials never appear in logs
- **Environment Variables** - Support for secure secret management

---

## Error Handling

- **Comprehensive Exception Handling** - Throughout all modules
- **Graceful Degradation** - Continue processing on single item failures
- **Detailed Logging** - Debug mode available for troubleshooting
- **Transaction Rollback** - Database integrity maintained on errors
- **User-Friendly Messages** - Clear error reporting to users
- **Retry Logic** - Automatic retry for transient failures

---

## Switching to Production

See **4_PRODUCTION_DEPLOYMENT.md** for complete production deployment guide.

### Quick Production Switch

1. **Clean all sandbox data**:
   ```bash
   sqlite3 data/billing.db "
   DELETE FROM invoice_history;
   DELETE FROM customer_settings;
   DELETE FROM domain_history;
   DELETE FROM monthly_highwater;
   DELETE FROM usage_data;
   DELETE FROM cos_discovery;
   DELETE FROM domains;
   DELETE FROM cos_mappings;
   DELETE FROM customers;
   DELETE FROM exclusions;
   DELETE FROM change_log;
   "
   ```

2. **Update `.env` file**:
   ```bash
   QBO_COMPANY_ID=<your-production-company-id>
   QBO_SANDBOX=false
   ```

3. **Clear sandbox authorization and re-authorize**:
   ```bash
   rm data/qbo_tokens.enc
   python3 -m src.ui.cli authorize-qbo
   ```

4. **Sync production customers**:
   ```bash
   python3 -m src.ui.cli sync-customers
   ```

5. **Test connection**:
   ```bash
   python3 -m src.ui.cli test-connections
   ```

### Finding Your Production Company ID

**Method 1: From QuickBooks URL**
1. Log into QuickBooks Online
2. Look at the URL: `https://app.qbo.intuit.com/app/homepage?realmId=XXXXXXXXXX`
3. The number after `realmId=` is your Company ID

**Method 2: From Authorization**
1. Run `authorize-qbo` command
2. The Company ID is displayed after successful authorization

---

## Important Notes

1. **Invoices are drafts** - All generated invoices are drafts by default, requiring manual review in QBO before sending
2. **Backup database** - Always backup before major operations
3. **Test with --skip-invoices** - Generate reports without creating invoices for testing
4. **OAuth tokens expire** - Tokens auto-refresh for 101 days, then require re-authorization
5. **CoS mapping** - Many CoS types need mapping. Run reconciliation to complete mappings
6. **Database cleanup** - Always clean the database when switching between sandbox and production

---

## Architecture Highlights

- **Separation of Concerns** - Clear module boundaries
- **Database-Driven** - All state in SQLite
- **Interactive Where Needed** - Prompts for important decisions
- **Automation-Friendly** - Can run fully unattended
- **Audit Trail** - Complete history of all operations
- **Production Ready** - Error handling, logging, testing

---

## Dependencies

- `paramiko` - SSH/SCP for Zimbra
- `sqlalchemy` - Database ORM
- `python-quickbooks` - QBO API
- `openpyxl` - Excel generation
- `click` - CLI framework
- `cryptography` - Token encryption
- `requests-oauthlib` - OAuth2

---

## Extensibility

The modular design allows easy extension:
- Add new report formats (extend parser)
- Support additional billing rules (modify calculator)
- Integrate other accounting systems (follow QBO pattern)
- Add web UI (import main workflow functions)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Mission Critical Email LLC. All rights reserved.

### Disclaimer

This software is provided "AS IS" without warranty of any kind, either express or implied, including but not limited to the implied warranties of merchantability and fitness for a particular purpose. Use at your own risk. In no event shall Mission Critical Email LLC be liable for any damages whatsoever arising out of the use of or inability to use this software.

### For Zimbra Partners

This application is open source and free to use, modify, and distribute for other Zimbra partners and users. Contributions are welcome!
