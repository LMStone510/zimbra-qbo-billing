# Step 3: Application Deployment and Sandbox Testing

**Version**: v1.13.0

**Goal**: Deploy the billing application on your workstation and test the complete billing workflow using QuickBooks Sandbox.

**Time Required**: 1-2 hours

**Prerequisites**:
- ✅ Completed Step 1: QBO Developer Setup (have your sandbox credentials)
- ✅ Completed Step 2: Zimbra Server Setup (usage reports being generated)
- Python 3.8+ installed on your workstation (macOS, Linux, or Windows)
- SSH access to your Zimbra server
- Git installed (to clone the repository)

---

## Overview

In this step, you'll:
1. Clone the billing application repository
2. Install Python dependencies
3. Configure the application for sandbox testing
4. Initialize the database
5. Authorize with QuickBooks Sandbox
6. Run a complete test billing cycle
7. Verify invoices and reports

By the end of this step, you'll have confirmed that the entire billing workflow works correctly before moving to production.

---

## Platform Compatibility

This application works on:
- ✅ **macOS** (10.15+) - Developed and tested
- ✅ **Linux** (Ubuntu 20.04+, Debian, RHEL, etc.)
- ✅ **Windows** (10/11 with Python 3.8+)

**Platform-Specific Notes:**
- **macOS/Linux**: Examples use `python3` and `pip3`
- **Windows**: You may use `python` and `pip` (without the `3`)
- **SSH Keys**: All platforms store SSH keys in `~/.ssh/` (Windows: `C:\Users\YourName\.ssh\`)

---

## Step 3.1: Clone the Repository

```bash
# Navigate to your preferred directory
cd ~

# Clone the repository
git clone https://github.com/LMStone510/zimbra-qbo-billing.git

# Enter the directory
cd zimbra-qbo-billing
```

---

## Step 3.2: Install Dependencies

```bash
# Install the application in development mode
pip3 install -e .
```

This installs all required Python packages and makes the `zimbra-billing` command available.

**Verify installation:**
```bash
python3 -m src.ui.cli --help
```

You should see a list of available commands.

---

## Step 3.3: Configure for Sandbox Testing

### Create `.env` Configuration File

The repository includes an example configuration. Copy and edit it:

```bash
cp .env.example .env
nano .env
```

**Configure with your Sandbox credentials from Step 1:**

```bash
# Zimbra Configuration
ZIMBRA_HOST=your-zimbra-server.com
ZIMBRA_USERNAME=ubuntu
ZIMBRA_KEY_FILE=~/.ssh/id_rsa
ZIMBRA_REPORT_PATH=/opt/MonthlyUsageReports

# QuickBooks Online Configuration - SANDBOX
QBO_CLIENT_ID=<your-development-client-id-from-step-1>
QBO_CLIENT_SECRET=<your-development-client-secret-from-step-1>
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_COMPANY_ID=<your-sandbox-company-id-from-step-1>
QBO_SANDBOX=true

# Database Configuration
DATABASE_PATH=data/billing.db
```

**Important Settings:**
- `QBO_SANDBOX=true` ← Must be `true` for sandbox testing
- `QBO_COMPANY_ID` ← Your sandbox company ID from Step 1
- `ZIMBRA_HOST` ← Your actual Zimbra server hostname
- `ZIMBRA_KEY_FILE` ← Path to your SSH private key

**Save and exit:**
- nano: Press `Ctrl+O`, `Enter`, then `Ctrl+X`
- vim: Press `ESC`, type `:wq`, press `Enter`

### (Optional) Configure Exclusions

If you want to exclude certain domains or CoS from billing:

```bash
cp data/config.json.example data/config.json
nano data/config.json
```

Add exclusion patterns:

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

---

## Step 3.4: Initialize the Database

```bash
python3 -m src.ui.cli init-db
```

**Expected output:**
```
Initializing database at data/billing.db...
✓ Database initialized successfully
✓ Tables created: customers, domains, cos_mappings, usage_data, ...
✓ Default data loaded
```

The database is now ready to store customer mappings, usage data, and invoice history.

---

## Step 3.5: Authorize QuickBooks Sandbox

```bash
python3 -m src.ui.cli authorize-qbo
```

**What happens:**
1. A browser window opens automatically
2. You're redirected to the Intuit authorization page
3. Sign in with your Intuit credentials
4. **IMPORTANT**: Select your **SANDBOX** company (not production)
5. Click "Authorize" to grant access
6. **Complete this immediately** - the authorization code expires quickly

**Expected output:**
```
Opening browser for QuickBooks authorization...
Waiting for authorization callback...
✓ Authorization successful!
  Company: Sandbox Company_YourName
  Company ID: 1234567890123456
  Environment: SANDBOX
✓ Tokens saved to data/qbo_tokens.enc
```

**Troubleshooting:**
- If browser doesn't open: Copy the URL from terminal and paste into browser
- If "Wrong company" selected: Run `authorize-qbo` again and select correct sandbox
- If "Timeout": The authorization code expired - run the command again

---

## Step 3.6: Sync Sandbox Customers

Import your sandbox customers into the application:

```bash
python3 -m src.ui.cli sync-customers
```

**Expected output:**
```
Syncing QuickBooks customers...
✓ Found 15 customers in QuickBooks
✓ Imported 15 customers to database
```

These customers will be available when mapping domains to customers during billing.

---

## Step 3.7: Test Connections

Verify everything is configured correctly:

```bash
python3 -m src.ui.cli test-connections
```

**Expected output:**
```
Testing connections...

Zimbra SSH Connection:
✓ SSH connection successful
✓ Can access /opt/MonthlyUsageReports/
✓ Found 4 usage reports

QuickBooks Online Connection:
✓ QuickBooks connection successful
  Company: Sandbox Company_YourName
  Company ID: 1234567890123456
  Environment: SANDBOX
✓ Can access customers (15 found)
✓ Can access items (8 found)

Database Connection:
✓ Database accessible at data/billing.db
✓ All tables present

✓ All connections successful!
```

**If any test fails**, review the error message and check your configuration in `.env`.

---

## Step 3.8: Run Your First Test Billing Cycle

Now for the exciting part - run a complete billing cycle with sandbox data!

### Choose a Test Month

Select a month where you have Zimbra usage reports (from Step 2):

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices
```

**Note**: We're using `--skip-invoices` for the first run to verify the data without creating invoices.

### What Happens During the Run

**[1/6] Fetching Zimbra Reports**
```
Fetching Zimbra usage reports for 2025-10...
✓ Found 4 weekly reports
✓ Downloaded to local cache
```

**[2/6] Parsing Usage Data**
```
Parsing usage reports...
✓ Parsed 87 domains
✓ Found 31 unique CoS types
✓ Calculated 151 monthly high-water marks
```

**[3/6] Domain Reconciliation** (Interactive)

You'll be prompted to map each domain to a QuickBooks customer:

```
New domain detected: acme-corp.com

Select customer:
 [1] Acme Corporation
 [2] Acme Industries
 [3] Acme LLC
 [4] <<Create New Customer>>
 [5] <<Skip This Domain>>

Choice (1-5): 1

✓ Mapped: acme-corp.com → Acme Corporation
```

**Tips:**
- Type the number and press Enter
- Choose option 4 to create a new customer (opens QuickBooks in browser)
- Choose option 5 to skip non-billable domains
- Mappings are saved - you won't be asked again for this domain

**[4/6] CoS Reconciliation** (Interactive)

You'll be prompted to map each Class of Service to a QuickBooks item:

```
New CoS detected: customer-50gb

Select QuickBooks item:
 [1] Email Hosting - 50GB Mailbox ($15.00)
 [2] Email Hosting - 25GB Mailbox ($10.00)
 [3] <<Skip This CoS>>

Choice (1-3): 1

✓ Mapped: customer-50gb → Email Hosting - 50GB Mailbox
  Price: $15.00 per mailbox per month
```

**Tips:**
- Match CoS names to the appropriate QuickBooks service items
- The price shown is what you configured in QuickBooks (Step 1)
- Mappings are saved for future months

**[5/6] Generating Report**
```
Generating Excel billing report...
✓ Report saved: data/billing_report_2025_10_20251030_143522.xlsx
```

**[6/6] Summary**
```
Billing Summary for October 2025:
  Domains processed: 87
  Billable domains: 85
  Skipped domains: 2
  Total line items: 69
  Total amount: $3,210.00

✓ Billing run completed successfully!
```

---

## Step 3.9: Review the Excel Report

Open the generated Excel report:

```bash
# macOS
open data/billing_report_2025_10_*.xlsx

# Linux
xdg-open data/billing_report_2025_10_*.xlsx

# Windows
start data/billing_report_2025_10_*.xlsx
```

**The report contains multiple sheets:**

### Sheet 1: Summary
- Total billing amount
- Number of domains/customers
- Breakdown by customer

### Sheet 2: Invoice Details
- One row per customer
- Line items with quantities and amounts
- Matches what will be in QuickBooks invoices

### Sheet 3: Domain Usage
- Detailed usage by domain and CoS
- High-water marks (maximum mailboxes during month)

**Verify:**
- ✅ All your domains are present
- ✅ Customer mappings are correct
- ✅ CoS mappings are correct
- ✅ Quantities match your expectations
- ✅ Pricing is accurate

---

## Step 3.10: Create Test Invoices in Sandbox

Once you're satisfied with the report, create the actual invoices in QuickBooks Sandbox:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-fetch --skip-reconciliation
```

**Flags explained:**
- `--skip-fetch` - Don't re-download Zimbra reports (use cached data)
- `--skip-reconciliation` - Don't prompt for mappings again (use saved mappings)

**What happens:**
```
[1/6] Using cached Zimbra reports... ✓
[2/6] Using cached usage data... ✓
[3/6] Using saved domain mappings... ✓
[4/6] Using saved CoS mappings... ✓
[5/6] Creating invoices in QuickBooks...
  Creating invoice for Acme Corporation... ✓
  Creating invoice for Beta Industries... ✓
  ...
  ✓ Created 69 invoices (all drafts)
[6/6] Generating report... ✓

✓ All invoices created successfully!
```

**Important**: All invoices are created as **DRAFTS** for your review before sending.

---

## Step 3.11: Verify Invoices in QuickBooks Sandbox

1. **Open your Sandbox Company**
   - Go to https://developer.intuit.com
   - Navigate to Sandbox → Sign in to Company

2. **View Invoices**
   - Click **Sales** → **Invoices**
   - Filter by **Draft** status
   - You should see all newly created invoices

3. **Review an Invoice**
   - Click any invoice to open it
   - Verify:
     - ✅ Correct customer
     - ✅ Line items match usage (CoS × quantity)
     - ✅ Pricing is correct
     - ✅ Total amount matches report

4. **Test Workflow** (Optional)
   - Try sending a test invoice (it won't actually send in sandbox)
   - Try marking an invoice as paid
   - Try deleting a draft invoice

---

## Step 3.12: Re-run Billing (Testing Idempotency)

The system prevents duplicate invoices. Try running the same month again:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

**Expected output:**
```
[4/6] Creating invoices in QuickBooks...
✓ Skipped 69 invoices (already exist for this month)

✓ No new invoices created
```

The system checks if invoices already exist for each customer/month combination and skips them.

---

## Troubleshooting

### SSH Connection Failed

**Error**: `Permission denied (publickey)`
```bash
# Test SSH manually
ssh -i ~/.ssh/id_rsa ubuntu@your-zimbra-server

# If fails, check:
ls -l ~/.ssh/id_rsa  # Should be 600 permissions
ssh-copy-id ubuntu@your-zimbra-server  # Re-copy public key
```

### QuickBooks Authorization Expired

**Error**: `Token expired`
```bash
# Re-authorize
python3 -m src.ui.cli authorize-qbo
```

OAuth tokens auto-refresh for 101 days, then require manual re-authorization.

### No Usage Reports Found

**Error**: `No reports found for 2025-10`
```bash
# Check Zimbra server
ssh ubuntu@your-zimbra-server ls -l /opt/MonthlyUsageReports/

# Run report script manually (see Step 2)
```

### Wrong Company Selected During Auth

**Error**: `Connected to production instead of sandbox`
```bash
# Clear tokens and re-authorize
rm data/qbo_tokens.enc
python3 -m src.ui.cli authorize-qbo
# Select SANDBOX company this time
```

### Database Locked

**Error**: `database is locked`
```bash
# Another process is using the database
# Find and close any other terminal sessions running the app
# Or wait a few seconds and try again
```

---

## Common Commands

```bash
# View all available commands
python3 -m src.ui.cli --help

# Test connections only
python3 -m src.ui.cli test-connections

# Sync customers from QBO
python3 -m src.ui.cli sync-customers

# Run full billing workflow
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10

# Generate report without invoices
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices

# Manually reconcile domains
python3 -m src.ui.cli reconcile-domains

# Manually reconcile CoS
python3 -m src.ui.cli reconcile-cos
```

---

## Summary Checklist

Before proceeding to Step 4, ensure you have:

- [ ] Cloned the repository
- [ ] Installed Python dependencies
- [ ] Configured `.env` with sandbox credentials
- [ ] Initialized the database
- [ ] Authorized with QuickBooks Sandbox
- [ ] Synced sandbox customers
- [ ] Tested all connections successfully
- [ ] Run a complete test billing cycle
- [ ] Reviewed the Excel report
- [ ] Created test invoices in sandbox
- [ ] Verified invoices in QuickBooks Sandbox
- [ ] Confirmed no duplicate invoices on re-run

---

## What's Next?

✅ **You've completed Step 3!**

You've successfully deployed the application and verified it works correctly with sandbox data.

**Next Step**: [4_PRODUCTION_DEPLOYMENT.md](4_PRODUCTION_DEPLOYMENT.md)

In Step 4, you'll:
1. Apply for and obtain Production OAuth credentials from Intuit
2. Clean the database of all sandbox test data
3. Switch to your Production QuickBooks company
4. Create your first real production invoices

---

## Additional Resources

- **5_USAGE.md** - Detailed command reference
- **PROJECT_REFERENCE.md** - Technical architecture and features
- **Troubleshooting**: Check logs in `data/logs/` for detailed error messages
