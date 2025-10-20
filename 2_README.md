# Zimbra-to-QuickBooks Billing Automation

**Status**: ✅ Fully operational and tested with QuickBooks Sandbox

Automated monthly billing system that:
- Fetches Zimbra email usage reports via SSH/SCP
- Calculates monthly high-water marks per domain/CoS
- Maps domains to QuickBooks Online customers
- Generates draft invoices in QBO
- Produces Excel summary reports

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

## Project Structure

```
invoicing/
├── src/                    # Source code
│   ├── database/          # Database models and queries
│   ├── zimbra/            # Zimbra report fetching and parsing
│   ├── qbo/               # QuickBooks Online integration
│   ├── reconciliation/    # Change detection and mapping
│   ├── reporting/         # Excel report generation
│   └── ui/                # CLI interface
├── data/                  # Data files
│   ├── billing.db         # SQLite database (created on init)
│   ├── config.json        # Configuration (optional)
│   ├── billing_report_*.xlsx  # Generated Excel reports
│   ├── qbo_tokens.enc     # Encrypted OAuth tokens
│   └── logs/              # Application logs
├── tests/                 # Test suite
├── .env                   # Environment configuration (primary)
└── requirements.txt       # Python dependencies
```

## Configuration

The application uses `.env` file for configuration (already configured):

```bash
# Zimbra Configuration
ZIMBRA_HOST=mb42.missioncriticalemail.com
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

## Switching to Production

See **3_SETUP_GUIDE.md** for the complete process, or **6_PRODUCTION.md** for production-specific details.

## Common Commands

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

## Documentation

Read in order:

1. **1_ZIMBRA_SERVER_SETUP.md** - 🔧 **START HERE!** Set up Zimbra server first
2. **2_README.md** (this file) - Quick reference and overview
3. **3_SETUP_GUIDE.md** - 📚 Complete guide from sandbox to production
4. **4_QUICKSTART.md** - 5-minute setup guide
5. **5_USAGE.md** - Detailed usage documentation
6. **6_PRODUCTION.md** - Production-specific setup instructions
7. **7_PROJECT_SUMMARY.md** - Technical architecture and features

## Current Status

✅ **Application fully functional and tested with QuickBooks Sandbox**

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

🚀 **Ready to switch to production** - See **PRODUCTION.md** for step-by-step instructions

## Switching to Production QuickBooks

### Prerequisites
1. Backup your database: `cp data/billing.db data/billing.db.sandbox-backup`
2. You'll need your **Production** QuickBooks Company ID

### Steps to Switch

1. **Update `.env` file**:
   ```bash
   nano .env
   ```

   Change these two lines:
   ```bash
   QBO_COMPANY_ID=<your-production-company-id>
   QBO_SANDBOX=false
   ```

2. **Clear sandbox authorization**:
   ```bash
   rm data/qbo_tokens.enc
   ```

3. **Re-authorize with Production**:
   ```bash
   python3 -m src.ui.cli authorize-qbo
   ```

   This will open your browser. Make sure you:
   - Select your **PRODUCTION** QuickBooks company (not sandbox)
   - Complete authorization immediately (don't wait)

4. **Sync production customers**:
   ```bash
   python3 -m src.ui.cli sync-customers
   ```

   This will import your real customers. You may have duplicate customers if you had sandbox customers with the same names.

5. **Re-map domains to production customers**:
   ```bash
   python3 -m src.ui.cli reconcile-domains
   ```

   You'll need to reassign all 85 domains to your production customers.

6. **Test connection**:
   ```bash
   python3 -m src.ui.cli test-connections
   ```

7. **Test with report only** (recommended):
   ```bash
   python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-invoices --skip-fetch
   ```

   This uses existing data and generates a report without creating invoices.

8. **Review and create invoices**:
   Once you're satisfied with the test report:
   ```bash
   python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation
   ```

### Finding Your Production Company ID

Two methods:

**Method 1: From QuickBooks URL**
1. Log into QuickBooks Online
2. Look at the URL: `https://app.qbo.intuit.com/app/homepage?realmId=XXXXXXXXXX`
3. The number after `realmId=` is your Company ID

**Method 2: From Authorization**
1. Run `authorize-qbo` command
2. The Company ID is displayed after successful authorization

### Reverting to Sandbox

If you need to go back to sandbox:
```bash
# Restore sandbox config
cp .env.sandbox-backup .env

# Or manually update .env:
# QBO_SANDBOX=true
# QBO_COMPANY_ID=9341455543932441

# Clear production tokens
rm data/qbo_tokens.enc

# Re-authorize with sandbox
python3 -m src.ui.cli authorize-qbo
# Select SANDBOX company during auth

# Sync sandbox customers
python3 -m src.ui.cli sync-customers
```

Note: You'll need to remap domains and CoS again since the database was cleaned.

## Important Notes

1. **Invoices are drafts** - All generated invoices are drafts by default, requiring manual review in QBO before sending
2. **Backup database** - Always backup before major operations
3. **Test with --skip-invoices** - Generate reports without creating invoices for testing
4. **OAuth tokens expire** - Tokens auto-refresh for 101 days, then require re-authorization
5. **CoS mapping** - Many CoS types need mapping. Run reconciliation to complete mappings

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Mission Critical Email LLC. All rights reserved.

### Disclaimer

This software is provided "AS IS" without warranty of any kind, either express or implied, including but not limited to the implied warranties of merchantability and fitness for a particular purpose. Use at your own risk. In no event shall Mission Critical Email LLC be liable for any damages whatsoever arising out of the use of or inability to use this software.

### For Zimbra Partners

This application is open source and free to use, modify, and distribute for other Zimbra partners and users. Contributions are welcome!
