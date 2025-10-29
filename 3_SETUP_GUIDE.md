# Complete Setup Guide: Sandbox to Production

This guide walks you through the entire process from initial installation, through sandbox testing, to production deployment.

## Platform Compatibility

This application works on:
- ✅ **macOS** (10.15+) - Developed and tested on macOS Tahoe
- ✅ **Linux** (Ubuntu 20.04+, Debian, RHEL, etc.) - All dependencies supported
- ✅ **Windows** (10/11 with Python 3.8+) - Fully compatible

**Requirements:**
- Python 3.8 or higher
- pip3 (Python package installer)
- SSH client (OpenSSH on Mac/Linux, built-in on Windows 10+)
- SSH keys configured for Zimbra server access

**Platform-Specific Notes:**
- **macOS/Linux**: Examples use `open` or `xdg-open` to view Excel files
- **Windows**: Use `start` instead of `open` to view Excel files, or double-click files in File Explorer
- **SSH Keys**: All platforms store SSH keys in `~/.ssh/` (Windows: `C:\Users\YourName\.ssh\`)

## Overview

The recommended approach is:
1. **Install and configure** with QuickBooks Sandbox
2. **Test thoroughly** with sandbox data
3. **Verify everything works** correctly
4. **Clean the database** of test data
5. **Switch to production** QuickBooks
6. **Go live** with real billing

**Total Time**: 2-3 hours for complete setup and testing

---

## Phase 1: Initial Installation

### Step 1.1: Install the Application

```bash
cd ~/zimbra-qbo-billing
pip3 install -e .
```

### Step 1.2: Verify Installation

```bash
python3 -m src.ui.cli --help
```

You should see a list of available commands.

---

## Phase 2: Sandbox Configuration

### Step 2.1: Set Up QuickBooks Sandbox

1. Go to https://developer.intuit.com
2. Sign in with your Intuit account
3. Create an app (or use existing app)
4. Note down:
   - **Client ID**
   - **Client Secret**
   - **Redirect URI**: `http://localhost:8080/callback`
5. Create a Sandbox Company:
   - Go to "Dashboard" → "Sandbox"
   - Click "Create sandbox company"
   - Note the Company ID (Realm ID)

### Step 2.2: Configure `.env` File

Your `.env` file should already exist. Edit it for sandbox:

```bash
nano .env
```

**Sandbox Configuration**:
```bash
# Zimbra Configuration
ZIMBRA_HOST=your-zimbra-server.com
ZIMBRA_USERNAME=ubuntu
ZIMBRA_KEY_FILE=~/.ssh/id_rsa
ZIMBRA_REPORT_PATH=/opt/MonthlyUsageReports

# QuickBooks Online Configuration - SANDBOX
QBO_CLIENT_ID=<your-sandbox-client-id>
QBO_CLIENT_SECRET=<your-sandbox-client-secret>
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_COMPANY_ID=<your-sandbox-company-id>
QBO_SANDBOX=true

# Database Configuration
DATABASE_PATH=data/billing.db
```

**Important Settings for Sandbox**:
- `QBO_SANDBOX=true` ← Must be true for sandbox
- `QBO_COMPANY_ID` ← Your sandbox company ID

Save and exit (Ctrl+O, Enter, Ctrl+X).

### Step 2.3: Optional - Configure `config.json`

The application primarily uses `.env`, but you can also use `config.json` for exclusions:

```bash
cp data/config.json.example data/config.json
nano data/config.json
```

Add any test domains or CoS patterns you want to exclude:

```json
{
  "exclusions": {
    "domains": [
      "*.test",
      "*-archive.com",
      "internal.company.com"
    ],
    "cos_patterns": [
      "*-test",
      "*-trial"
    ]
  }
}
```

---

## Phase 3: Sandbox Setup

### Step 3.1: Initialize Database

```bash
python3 -m src.ui.cli init-db
```

**Expected output**:
```
Creating database at data/billing.db
✓ Database initialized successfully
```

### Step 3.2: Authorize QuickBooks Sandbox

```bash
python3 -m src.ui.cli authorize-qbo
```

**What happens**:
1. Browser opens to Intuit authorization page
2. Sign in if needed
3. **IMPORTANT**: Select your **SANDBOX** company from dropdown
4. Click "Authorize"
5. Complete authorization **immediately** (don't wait)

**Expected output**:
```
Opening browser for authorization...
Waiting for authorization...
✓ Authorization successful
Company ID: 1234567890
Tokens saved to data/qbo_tokens.enc
```

**Troubleshooting**:
- If timeout occurs, the authorization code expires after a few minutes
- Just run the command again and complete it faster
- Make sure you select SANDBOX company, not production

### Step 3.3: Sync Sandbox Customers

Import customers from your sandbox company:

```bash
python3 -m src.ui.cli sync-customers
```

**Expected output**:
```
Syncing QuickBooks customers...
✓ Synced 29 customers
```

The number will vary based on your sandbox company.

### Step 3.4: Test Connections

Verify everything is connected:

```bash
python3 -m src.ui.cli test-connections
```

**Expected output**:
```
Testing Zimbra SSH connection...
✓ Zimbra connection successful
  Found 41 report files

Testing QuickBooks Online connection...
✓ QuickBooks connection successful
  Company: Sandbox Company_<your-name>
  Company ID: 1234567890
  Environment: SANDBOX
```

**Important**: Verify it says "Environment: SANDBOX"

---

## Phase 4: Sandbox Testing

### Step 4.1: Run First Test Billing (Report Only)

Run billing for a test month without creating invoices:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-invoices
```

**What happens**:
1. Fetches Zimbra reports via SSH
2. Parses domains and CoS usage
3. Prompts you to assign domains to customers (interactive)
4. Prompts you to map CoS to QuickBooks items (interactive)
5. Generates Excel report
6. Does NOT create invoices

**Example prompts you'll see**:

```
Found 87 new domains

Domain: example.com
Select customer number [0 to skip]:
1. Acme Corp
2. Beta Industries
3. Gamma LLC
...
Select customer number [0 to skip]: 2
✓ Assigned example.com to Beta Industries
```

```
Found 31 new CoS types

CoS: customer-50gb (Quota: 50GB)
Select item number [0 to skip]:
1. Email Hosting - 50GB ($10.00)
2. Email Hosting - 100GB ($15.00)
...
Select item number [0 to skip]: 1
Unit price: $10.00
✓ Mapped customer-50gb to Email Hosting - 50GB at $10.00
```

**Tips**:
- Enter 0 to skip domains you don't want to bill
- Enter 0 to skip CoS types that shouldn't be billed
- You can map domains to any customer in your sandbox
- This process will take 20-40 minutes depending on domain count

**Expected output**:
```
[5/6] Generating Excel report...
      Report saved to: data/billing_report_2025_03_20251020_143022.xlsx

Billing Summary:
Billing Period: 2025-03
Total Customers: 50
Total Amount: $3,210.00
Total Line Items: 69

✓ Monthly billing completed successfully!
```

### Step 4.2: Review the Excel Report

```bash
# macOS
open data/billing_report_2025_03_*.xlsx

# Linux
xdg-open data/billing_report_2025_03_*.xlsx

# Windows
start data/billing_report_2025_03_*.xlsx
```

**Review**:
- Check customer names are correct
- Verify item descriptions match your services
- Confirm quantities make sense
- Check prices are correct
- Verify totals calculate properly

### Step 4.3: Test Invoice Creation

Now test creating actual invoices in sandbox:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation
```

**Flags explained**:
- `--skip-fetch` - Use existing report data (don't re-download)
- `--skip-reconciliation` - Skip domain/CoS mapping (already done)

**Expected output**:
```
[4/6] Creating invoices in QuickBooks...
      Created 50 draft invoices

Billing Summary:
Invoices Created: 50
Total Amount: $3,210.00
```

### Step 4.4: Verify Invoices in QuickBooks Sandbox

1. Log into QuickBooks Sandbox: https://app.sandbox.qbo.intuit.com
2. Go to **Sales** → **Invoices**
3. Filter by **Status: Draft**
4. Review several invoices:
   - ✓ Correct customer
   - ✓ Line items are correct
   - ✓ Prices are correct
   - ✓ Totals are correct
   - ✓ Date is first of next month
   - ✓ Memo says "Zimbra Email Services - March 2025"

### Step 4.5: Test Additional Features

**Preview invoices**:
```bash
python3 -m src.ui.cli preview-invoices --year 2025 --month 3
```

**Manual reconciliation**:
```bash
# Add more domain mappings
python3 -m src.ui.cli reconcile-domains

# Add more CoS mappings
python3 -m src.ui.cli reconcile-cos
```

**Generate report for different month**:
```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 4 --skip-invoices
```

---

## Phase 5: Verification Checklist

Before moving to production, verify:

- [ ] Zimbra SSH connection works reliably
- [ ] Reports download successfully
- [ ] Parser correctly extracts domains and CoS
- [ ] Interactive reconciliation prompts work
- [ ] Domain-to-customer mapping works correctly
- [ ] CoS-to-item mapping works correctly
- [ ] Prices are pulled from QuickBooks items
- [ ] Excel reports generate with correct data
- [ ] Draft invoices appear in QuickBooks
- [ ] Invoice line items are correct
- [ ] Invoice totals are correct
- [ ] No errors in logs (`data/logs/*.log`)
- [ ] All expected features work as intended

**If anything doesn't work**, troubleshoot in sandbox before moving to production.

---

## Phase 6: Clean Database for Production

Once you've verified everything works in sandbox, clean the test data:

### Step 6.1: Backup Sandbox Configuration

```bash
cd ~/zimbra-qbo-billing
cp .env .env.sandbox-backup
cp data/billing.db data/billing.db.sandbox-backup
```

This allows you to return to sandbox if needed.

### Step 6.2: Clean All Test Data

**Option A: Database Cleanup Script (Recommended)**

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

Verify it's clean:
```bash
sqlite3 data/billing.db "
SELECT 'Customers: ' || COUNT(*) FROM customers;
SELECT 'Domains: ' || COUNT(*) FROM domains;
SELECT 'CoS mappings: ' || COUNT(*) FROM cos_mappings;
"
```

Should show 0 for everything.

**Option B: Reinitialize Database (Alternative)**

```bash
# Backup old database
mv data/billing.db data/billing.db.sandbox-backup

# Create fresh database
python3 -m src.ui.cli init-db
```

### Step 6.3: Clean Old Reports and Invoices

```bash
# Archive old sandbox reports
mkdir -p data/archive
mv data/billing_report_*.xlsx data/archive/
```

### Step 6.4: Clean QuickBooks Tokens

```bash
rm data/qbo_tokens.enc
```

This forces re-authorization with production.

---

## Phase 7: Production Configuration

### Step 7.1: Get Production QuickBooks Details

You'll need:
1. **Production Company ID** (Realm ID)
2. Same **Client ID** and **Client Secret** (works for both sandbox and production)

**Find your Production Company ID**:

**Method 1 - From QuickBooks URL**:
1. Log into production QuickBooks: https://qbo.intuit.com
2. Look at URL: `https://app.qbo.intuit.com/app/homepage?realmId=1234567890`
3. Copy the number after `realmId=`

**Method 2 - From Authorization** (see Step 7.3):
The authorization process displays it.

### Step 7.2: Update `.env` for Production

```bash
nano .env
```

**Change these lines**:

**BEFORE (Sandbox)**:
```bash
QBO_COMPANY_ID=<your-sandbox-company-id>
QBO_SANDBOX=true
```

**AFTER (Production)**:
```bash
QBO_COMPANY_ID=<your-production-company-id>
QBO_SANDBOX=false
```

**CRITICAL**:
- Set `QBO_SANDBOX=false` (not true)
- Use your PRODUCTION Company ID

Leave all other settings unchanged:
- Keep same Client ID
- Keep same Client Secret
- Keep same Redirect URI
- Keep same Zimbra settings

Save and exit.

### Step 7.3: Verify Configuration

Double-check your `.env`:

```bash
grep QBO_ .env
```

Should show:
```
QBO_CLIENT_ID=<your-id>
QBO_CLIENT_SECRET=<your-secret>
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_COMPANY_ID=<production-company-id>
QBO_SANDBOX=false
```

**Make sure `QBO_SANDBOX=false`** ← This is the most important setting!

---

## Phase 8: Production Setup

### Step 8.1: Authorize Production QuickBooks

```bash
python3 -m src.ui.cli authorize-qbo
```

**CRITICAL**:
1. Browser opens to Intuit login
2. Sign in if needed
3. **SELECT YOUR PRODUCTION COMPANY** (not sandbox!)
4. Click "Authorize"
5. **Complete immediately** (don't wait)

**Expected output**:
```
Opening browser for authorization...
Waiting for authorization...
✓ Authorization successful
Company ID: <your-production-id>
Environment: PRODUCTION
Tokens saved to data/qbo_tokens.enc
```

**Verify it says "Environment: PRODUCTION"** ← Very important!

### Step 8.2: Test Production Connection

```bash
python3 -m src.ui.cli test-connections
```

**Expected output**:
```
Testing Zimbra SSH connection...
✓ Zimbra connection successful

Testing QuickBooks Online connection...
✓ QuickBooks connection successful
  Company: <Your Production Company Name>
  Company ID: <your-production-id>
  Environment: PRODUCTION
```

**STOP HERE IF**:
- It says "SANDBOX" instead of "PRODUCTION"
- Company name is wrong
- Any errors occur

If wrong, go back to Step 7.2 and fix `.env`, then repeat from 8.1.

### Step 8.3: Sync Production Customers

```bash
python3 -m src.ui.cli sync-customers
```

**Expected output**:
```
Syncing QuickBooks customers...
✓ Synced 150 customers
```

Number will vary based on your real customer count.

**Verify**:
```bash
sqlite3 data/billing.db "SELECT customer_name FROM customers LIMIT 10;"
```

Should show your REAL customer names, not sandbox test names.

### Step 8.4: Map Domains to Production Customers

Now map all domains to your real customers:

```bash
python3 -m src.ui.cli reconcile-domains
```

**What happens**:
- Shows each domain from Zimbra reports
- Lists your REAL customers
- You assign each domain to correct customer

**Tips**:
- Have a list ready of which domains belong to which customers
- Enter 0 to skip domains that shouldn't be billed
- This will take 20-40 minutes for ~87 domains
- Take your time - these mappings affect real billing

**Example**:
```
Found 87 unmapped domains

Domain: acmecorp.com
Select customer number [0 to skip]:
1. Acme Corporation
2. Acme Industries
3. Acme LLC
...
Select customer number [0 to skip]: 1
✓ Assigned acmecorp.com to Acme Corporation
```

### Step 8.5: Map CoS to Production Items

Map Class of Service types to your QuickBooks service items:

```bash
python3 -m src.ui.cli reconcile-cos
```

**What happens**:
- Shows each CoS type from reports (e.g., customer-50gb)
- Lists your real QuickBooks service items
- You map each CoS to the appropriate item

**Tips**:
- The CoS name often indicates the mailbox size (50gb, 100gb, etc.)
- Match to your pricing structure
- Prices are pulled from QuickBooks items
- You can update items in QuickBooks if prices are wrong

**Example**:
```
Found 31 unmapped CoS types

CoS: customer-50gb (Quota: 50GB)
Select item number [0 to skip]:
1. Email Hosting - 50GB ($10.00/mo)
2. Email Hosting - 100GB ($15.00/mo)
3. Email Hosting - 200GB ($25.00/mo)
...
Select item number [0 to skip]: 1
Unit price from item: $10.00
✓ Mapped customer-50gb to Email Hosting - 50GB at $10.00/mo
```

---

## Phase 9: Production Testing (Critical!)

### Step 9.1: Test Run WITHOUT Invoices

**IMPORTANT**: Test first without creating real invoices!

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation --skip-invoices
```

**Flags**:
- `--skip-fetch` - Use existing report data
- `--skip-reconciliation` - Don't prompt for mappings
- `--skip-invoices` - Don't create invoices in QuickBooks

**Expected output**:
```
[5/6] Generating Excel report...
      Report saved to: data/billing_report_2025_03_20251020_150523.xlsx

Billing Summary:
Billing Period: 2025-03
Total Customers: 50
Total Amount: $3,210.00
```

### Step 9.2: Review Production Excel Report

```bash
# macOS
open data/billing_report_2025_03_*.xlsx

# Linux
xdg-open data/billing_report_2025_03_*.xlsx

# Windows
start data/billing_report_2025_03_*.xlsx
```

**CAREFULLY REVIEW**:
- [ ] Customer names are your REAL customers
- [ ] All domains assigned to correct customers
- [ ] Item descriptions match your services
- [ ] Prices are correct (check against your pricing)
- [ ] Quantities make sense for each customer
- [ ] Totals are reasonable
- [ ] No test/sandbox data appears

**If anything is wrong**:
- Fix domain mappings: `python3 -m src.ui.cli reconcile-domains`
- Fix CoS mappings: `python3 -m src.ui.cli reconcile-cos`
- Update prices in QuickBooks items if needed
- Re-run test report

### Step 9.3: Preview Invoices

Preview what invoices will look like:

```bash
python3 -m src.ui.cli preview-invoices --year 2025 --month 3
```

Review several customers to verify correctness.

---

## Phase 10: Go Live with Production

### Step 10.1: Create REAL Draft Invoices

Once you've verified everything is correct:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation
```

**This creates REAL invoices** in your production QuickBooks!

**Expected output**:
```
[4/6] Creating invoices in QuickBooks...
      Created 50 draft invoices

Billing Summary:
Invoices Created: 50
Total Amount: $3,210.00
```

### Step 10.2: Review Draft Invoices in QuickBooks

1. Log into production QuickBooks: https://qbo.intuit.com
2. Go to **Sales** → **Invoices**
3. Filter by **Status: Draft**
4. Review several invoices carefully
5. Make any corrections needed

**Check**:
- Correct customer
- All line items correct
- Descriptions accurate
- Prices correct
- Totals match Excel report
- Invoice date (should be first of next month)

### Step 10.3: Send Invoices to Customers

Once invoices are verified:

1. In QuickBooks, select invoices to send
2. Click **Save and Send**
3. Customize email message if needed
4. Send to customers

**OR** send them in batches:
- Review and send a few test invoices first
- Verify customers receive them correctly
- Then send the rest

---

## Phase 11: Ongoing Operations

### Monthly Billing Workflow

**On the 1st of each month** (or your billing day):

```bash
cd ~/zimbra-qbo-billing

# Run billing for previous month
python3 -m src.ui.cli run-monthly-billing --skip-reconciliation

# Review Excel report (use command for your OS)
open data/billing_report_YYYY_MM_*.xlsx        # macOS
xdg-open data/billing_report_YYYY_MM_*.xlsx    # Linux
start data/billing_report_YYYY_MM_*.xlsx       # Windows

# Review draft invoices in QuickBooks
# Send when ready
```

**Flags**:
- Use `--skip-reconciliation` for unattended runs
- New domains will be skipped until you manually reconcile them
- You can reconcile monthly or as needed

### Periodic Reconciliation

**When needed** (new domains, new CoS types):

```bash
# Map any new domains
python3 -m src.ui.cli reconcile-domains

# Map any new CoS types
python3 -m src.ui.cli reconcile-cos
```

### Database Backup

**Before each monthly run**:

```bash
cp data/billing.db data/billing.db.$(date +%Y%m%d)
```

### Automation (Optional)

**macOS/Linux** - Set up cron job for automatic monthly runs:

```bash
crontab -e
```

Add:
```bash
# Run billing at 6am on 1st of each month
0 6 1 * * cd ~/zimbra-qbo-billing && /usr/bin/python3 -m src.ui.cli run-monthly-billing --skip-reconciliation >> data/logs/cron.log 2>&1
```

**Windows** - Use Task Scheduler:
1. Open Task Scheduler → Create Basic Task
2. Name: "Zimbra Monthly Billing"
3. Trigger: Monthly, Day 1, 6:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `-m src.ui.cli run-monthly-billing --skip-reconciliation`
   - Start in: `C:\path\to\zimbra-qbo-billing`
5. Additional settings:
   - Run whether user is logged on or not
   - Run with highest privileges
   - Configure output logging in the script arguments if desired

---

## Troubleshooting

### Wrong Environment After Authorization

**Symptom**: Connected to sandbox when you wanted production (or vice versa)

**Fix**:
1. Check `.env` - verify `QBO_SANDBOX=false` for production
2. Delete tokens: `rm data/qbo_tokens.enc`
3. Re-authorize: `python3 -m src.ui.cli authorize-qbo`
4. Select correct company during authorization

### Wrong Company Selected

**Symptom**: Authorized but wrong company

**Fix**:
1. Delete tokens: `rm data/qbo_tokens.enc`
2. Re-authorize: `python3 -m src.ui.cli authorize-qbo`
3. Pay close attention to company dropdown
4. Select the correct company

### Can't Find Production Company ID

**Symptom**: Don't know production Company ID

**Fix**:
1. Log into QuickBooks: https://qbo.intuit.com
2. Look at URL bar
3. Find `realmId=XXXXXXXXXX`
4. That's your Company ID

### Authorization Code Timeout

**Symptom**: "Token invalid" or timeout error

**Fix**:
1. Run authorization again
2. Complete it within 2-3 minutes
3. Don't switch tabs or wait

### Need to Switch Back to Sandbox

**Symptom**: Need to test something in sandbox again

**Fix**:
```bash
# 1. Clean production data
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

# 2. Restore sandbox config
cp .env.sandbox-backup .env

# 3. Clear production tokens
rm data/qbo_tokens.enc

# 4. Re-authorize sandbox
python3 -m src.ui.cli authorize-qbo
# Select SANDBOX company

# 5. Sync sandbox customers
python3 -m src.ui.cli sync-customers
```

**Important**: Always clean the database when switching to avoid mixing sandbox and production data.

### Clear Everything and Start Over

**Symptom**: Messed up and want to reset

**Fix**:
```bash
# Backup if needed
cp data/billing.db data/billing.db.backup

# Reinitialize
python3 -m src.ui.cli init-db

# Re-authorize
rm data/qbo_tokens.enc
python3 -m src.ui.cli authorize-qbo

# Sync customers
python3 -m src.ui.cli sync-customers

# Remap everything
python3 -m src.ui.cli reconcile-domains
python3 -m src.ui.cli reconcile-cos
```

---

## Configuration Summary

### `.env` File Settings

**For Sandbox**:
```bash
QBO_COMPANY_ID=<sandbox-company-id>
QBO_SANDBOX=true
```

**For Production**:
```bash
QBO_COMPANY_ID=<production-company-id>
QBO_SANDBOX=false
```

**Stays the same** for both:
- `QBO_CLIENT_ID`
- `QBO_CLIENT_SECRET`
- `QBO_REDIRECT_URI`
- `ZIMBRA_HOST`
- `ZIMBRA_USERNAME`
- All other settings

### `config.json` File (Optional)

Used for exclusion patterns - same for both sandbox and production:

```json
{
  "exclusions": {
    "domains": ["*.test", "*-archive"],
    "cos_patterns": ["*-test", "*-trial"]
  }
}
```

---

## Checklist Summary

### Sandbox Setup ✓
- [ ] Install application
- [ ] Configure `.env` with sandbox settings (`QBO_SANDBOX=true`)
- [ ] Initialize database
- [ ] Authorize sandbox QuickBooks
- [ ] Sync sandbox customers
- [ ] Test connections (verify "SANDBOX")
- [ ] Run test billing
- [ ] Review test report
- [ ] Create test invoices
- [ ] Verify invoices in sandbox QuickBooks
- [ ] Test all features

### Clean and Switch ✓
- [ ] Backup `.env` and database
- [ ] Clean database (delete all test data)
- [ ] Delete old reports
- [ ] Delete QuickBooks tokens
- [ ] Update `.env` with production settings (`QBO_SANDBOX=false`)
- [ ] Verify configuration

### Production Setup ✓
- [ ] Authorize production QuickBooks
- [ ] Test connections (verify "PRODUCTION")
- [ ] Sync production customers
- [ ] Verify customer list is correct
- [ ] Map all domains to real customers
- [ ] Map all CoS to real items
- [ ] Test run without invoices
- [ ] Review production Excel report carefully
- [ ] Preview production invoices
- [ ] Verify all mappings and prices are correct

### Go Live ✓
- [ ] Create real draft invoices
- [ ] Review drafts in QuickBooks
- [ ] Make any needed corrections
- [ ] Send invoices to customers
- [ ] Set up monthly workflow
- [ ] Configure backups
- [ ] Optional: Set up automation

---

## Quick Reference

### Key Commands

```bash
# Authorization
python3 -m src.ui.cli authorize-qbo

# Sync customers
python3 -m src.ui.cli sync-customers

# Test connections
python3 -m src.ui.cli test-connections

# Reconcile
python3 -m src.ui.cli reconcile-domains
python3 -m src.ui.cli reconcile-cos

# Monthly billing
python3 -m src.ui.cli run-monthly-billing --skip-reconciliation

# Test run (no invoices)
python3 -m src.ui.cli run-monthly-billing --skip-invoices

# Preview
python3 -m src.ui.cli preview-invoices --year 2025 --month 3
```

### Key Files

- **`.env`** - Main configuration (sandbox vs production)
- **`config.json`** - Optional exclusions
- **`data/billing.db`** - SQLite database
- **`data/qbo_tokens.enc`** - OAuth tokens (encrypted)
- **`data/billing_report_*.xlsx`** - Excel reports
- **`data/logs/*.log`** - Application logs

### Security Best Practices

#### SSH Host Key Verification

For secure connections to your Zimbra server, add it to known_hosts:

```bash
ssh-keyscan -H your-zimbra-host.com >> ~/.ssh/known_hosts
```

The system uses strict host key verification by default, which prevents MITM attacks.

#### OAuth Token Security

- Tokens are encrypted at rest using Fernet encryption
- Token encryption keys stored in `data/.qbo_key` with restrictive permissions
- Tokens automatically masked in logs
- Never commit `.qbo_key` or `qbo_tokens.enc` to version control

#### Database Migrations

The system automatically applies schema updates when needed. See `MIGRATION_GUIDE.md` for details on:
- Automatic migration process
- Manual migration if needed
- Backup and rollback procedures

#### Idempotency Protection

The system prevents duplicate invoice creation:
- Safe to re-run billing for same period
- Invoices are tracked by unique idempotency key
- System skips already-created invoices automatically

#### Automation Security

For automated/scheduled runs, use the `--non-interactive` flag:

```bash
python3 -m src.ui.cli run-monthly-billing --non-interactive --json-output summary.json
```

Benefits:
- No prompts that could hang automation
- JSON output for monitoring
- Safe duplicate prevention
- Clear reporting of skipped items

See `5_USAGE.md` for detailed automation examples.

### Support

- **2_README.md** - Quick reference
- **3_SETUP_GUIDE.md** (this file) - Complete setup guide
- **4_QUICKSTART.md** - Quick reference
- **5_USAGE.md** - Detailed usage
- **6_PRODUCTION.md** - Production-specific details
- **7_PROJECT_SUMMARY.md** - Technical overview
- **MIGRATION_GUIDE.md** - Database migration documentation

---

**You are here**: Ready to start! Begin with Phase 1: Initial Installation.
