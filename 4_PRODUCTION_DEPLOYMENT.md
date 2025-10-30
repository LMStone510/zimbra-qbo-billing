# Step 4: Production Deployment

**Version**: v1.13.0

**Goal**: Apply for Production OAuth credentials, clean the sandbox data, switch to your Production QuickBooks company, and create your first real invoices.

**Time Required**: 1-2 hours

**Prerequisites**:
- ✅ Completed Step 3: Application Deployment (sandbox testing successful)
- ✅ Have a QuickBooks Online production account
- ✅ All production customers exist in QuickBooks Online
- ✅ All service items (for CoS mapping) exist in QuickBooks Online

---

## Overview

In this step, you'll transition from sandbox testing to production use. This involves:
1. Applying for and obtaining Production OAuth credentials from Intuit
2. Preparing your production QuickBooks company
3. Cleaning all sandbox data from the database
4. Switching configuration to production
5. Authorizing with your production QuickBooks company
6. Importing real customers
7. Mapping domains and CoS to production data
8. Creating your first production invoices (as drafts for review)

**Important**: This step is irreversible - you'll be working with real customer data and creating real invoices. Proceed carefully and follow all steps.

---

## Step 4.1: Apply for Production OAuth Credentials

Before you can connect to your production QuickBooks, you need production OAuth credentials.

### 1. Complete Your App Profile

1. **Go to Intuit Developer Portal**
   - Navigate to: https://developer.intuit.com
   - Sign in and go to **"My Apps"**
   - Select your application (created in Step 1)

2. **Complete App Information**
   - Click **"App Info"** in the left menu
   - Fill in required fields:
     - **App Name**: `Zimbra Billing Automation` (or your company name)
     - **App Description**: Detailed description of what your app does
     - **App Website**: Your company website or GitHub repository URL
     - **Privacy Policy URL**: Your privacy policy or use GitHub repo
     - **Terms of Service URL**: Your terms or use GitHub repo
     - **App Logo**: Upload a logo (optional but recommended)

3. **Configure OAuth Scopes**
   - Click **"Keys & credentials"**
   - Under **Scopes**, ensure these are selected:
     - ✅ `com.intuit.quickbooks.accounting` - Full accounting access
   - Save changes

### 2. Submit for Production

1. **Go to Production Tab**
   - Click **"Production"** in the left menu
   - Or click **"Go to Production"** button

2. **Review Requirements**
   - Intuit will show production requirements checklist
   - Ensure all items are completed:
     - ✅ App information complete
     - ✅ Privacy policy URL provided
     - ✅ Terms of service URL provided
     - ✅ Redirect URI configured

3. **Submit for Review**
   - Click **"Submit for Production"**
   - Intuit typically approves within minutes to hours
   - You'll receive an email when approved

### 3. Get Production Credentials

Once approved:

1. **Navigate to Keys & Credentials**
2. **Switch to Production Tab** (at top of page)
3. **Copy Production Credentials**:
   - **Production Client ID**: Copy and save securely
   - **Production Client Secret**: Click "Show", then copy and save
   - **Redirect URI**: Should still be `http://localhost:8080/callback`

**⚠️ IMPORTANT**: Production credentials are different from Development credentials. Keep them secure!

---

## Step 4.2: Prepare Production QuickBooks Company

Ensure your production QuickBooks has everything needed for billing.

### 1. Verify Service Items

1. **Sign in to Production QuickBooks**
   - Go to: https://qbo.intuit.com
   - Sign in with your production credentials

2. **Check Products and Services**
   - Click Gear icon (⚙️) → **Products and Services**
   - Verify you have service items for each CoS type you bill for

3. **Create Missing Items** (if needed)
   - Click **New** → **Service**
   - Name: "Email Hosting - 2GB Mailbox" (example)
   - Sales Price: Your rate per mailbox
   - Income Account: Select appropriate revenue account
   - **Save and close**

### 2. Verify Customers

1. **Check Customers List**
   - Click **Sales** → **Customers**
   - Ensure all customers you bill are present

2. **Add Missing Customers** (if needed)
   - Click **New Customer**
   - Fill in customer details
   - **Save**

### 3. Find Your Production Company ID

**Option A: From URL**
1. While signed into production QBO, look at browser URL
2. You'll see: `https://app.qbo.intuit.com/app/homepage?realmId=1234567890`
3. Copy the number after `realmId=` - this is your Company ID

**Option B: From Authorization** (you'll see it during Step 4.4)

---

## Step 4.3: Backup and Clean Sandbox Data

**⚠️ CRITICAL**: This removes ALL sandbox test data. Make sure you've completed all sandbox testing first!

### 1. Backup Current Configuration

```bash
cd ~/zimbra-qbo-billing

# Backup .env file
cp .env .env.sandbox-backup

# Backup database (optional - contains test data only)
cp data/billing.db data/billing.db.sandbox-backup
```

### 2. Clean ALL Sandbox Data

This SQL command removes all sandbox test data from the database:

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

**What this does:**
- ✅ Removes all sandbox customers and mappings
- ✅ Clears all test invoice history
- ✅ Removes all domain and CoS mappings
- ✅ Clears all cached usage data
- ✅ Ensures complete separation of test and production data

**Verification**:
```bash
sqlite3 data/billing.db "SELECT COUNT(*) FROM customers;"
```

Should return `0` - database is now clean.

---

## Step 4.4: Configure for Production

### 1. Update `.env` File

Edit your configuration to use production credentials:

```bash
nano .env
```

**Update these lines:**

```bash
# QuickBooks Online Configuration - PRODUCTION
QBO_CLIENT_ID=<your-PRODUCTION-client-id>
QBO_CLIENT_SECRET=<your-PRODUCTION-client-secret>
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_COMPANY_ID=<your-production-company-id>
QBO_SANDBOX=false
```

**Critical Changes:**
- `QBO_CLIENT_ID` → Use **Production** Client ID (from Step 4.1)
- `QBO_CLIENT_SECRET` → Use **Production** Client Secret (from Step 4.1)
- `QBO_COMPANY_ID` → Use your **production** Company ID (from Step 4.2)
- `QBO_SANDBOX=false` ← MUST be `false` for production!

**Zimbra settings remain the same** (unchanged from sandbox testing).

Save and exit (Ctrl+O, Enter, Ctrl+X).

### 2. Clear Sandbox Authorization Tokens

```bash
rm data/qbo_tokens.enc
rm data/.qbo_key
```

This forces a fresh authorization with production credentials.

---

## Step 4.5: Authorize Production QuickBooks

**⚠️ IMPORTANT**: You're about to authorize with PRODUCTION QuickBooks. This is your real company data.

```bash
python3 -m src.ui.cli authorize-qbo
```

**What happens:**
1. Browser opens to Intuit authorization page
2. Sign in with your Intuit credentials
3. **SELECT YOUR PRODUCTION COMPANY** (very important!)
4. Review permissions requested
5. Click **"Authorize"**
6. **Complete immediately** - code expires quickly

**Expected output:**
```
Opening browser for QuickBooks authorization...
Waiting for authorization callback...
✓ Authorization successful!
  Company: Your Company Name LLC
  Company ID: 9876543210
  Environment: PRODUCTION
✓ Tokens saved to data/qbo_tokens.enc
```

**Verify Environment Shows "PRODUCTION"** - if it says "SANDBOX", you selected the wrong company!

---

## Step 4.6: Test Production Connection

Verify the production connection works:

```bash
python3 -m src.ui.cli test-connections
```

**Expected output:**
```
Testing connections...

Zimbra SSH Connection:
✓ SSH connection successful
✓ Can access /opt/MonthlyUsageReports/

QuickBooks Online Connection:
✓ QuickBooks connection successful
  Company: Your Company Name LLC
  Company ID: 9876543210
  Environment: PRODUCTION
✓ Can access customers
✓ Can access items

Database Connection:
✓ Database accessible

✓ All connections successful!
```

**⚠️ If "Environment" shows SANDBOX:**
- You connected to the wrong company
- Run: `rm data/qbo_tokens.enc`
- Run: `python3 -m src.ui.cli authorize-qbo` again
- Select PRODUCTION company this time

---

## Step 4.7: Sync Production Customers

Import your real customers from production QuickBooks:

```bash
python3 -m src.ui.cli sync-customers
```

**Expected output:**
```
Syncing QuickBooks customers...
✓ Found 150 customers in QuickBooks
✓ Imported 150 customers to database
```

The number depends on how many customers you have in QuickBooks.

**Verify customers imported:**
```bash
sqlite3 data/billing.db "SELECT customer_name FROM customers ORDER BY customer_name LIMIT 10;"
```

You should see your real customer names.

---

## Step 4.8: Run First Production Billing (Report Only)

**Test with --skip-invoices first** to verify everything before creating real invoices:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-invoices
```

**What happens:**

### [1/6] Fetching Zimbra Reports
```
Fetching reports for 2025-10...
✓ Found 4 weekly reports
✓ Downloaded and cached
```

### [2/6] Parsing Usage Data
```
Parsing usage reports...
✓ Parsed 87 domains
✓ Found 31 unique CoS types
✓ Calculated 151 high-water marks
```

### [3/6] Domain Reconciliation (Interactive)

You'll map each domain to a PRODUCTION customer:

```
New domain found: acme-corp.com

Available customers:
  0: Skip (don't assign)
  1: ACME Corporation (QBO ID: 12345)
  2: Acme Industries LLC (QBO ID: 12346)
  3: Acme Enterprises (QBO ID: 12347)

Select customer number [0]: 1

✓ Assigned acme-corp.com to ACME Corporation
```

**Important Tips:**
- Choose carefully - these are your REAL customers
- Choose 0 to skip non-billable domains
- Mappings are permanent (can be changed later if needed)
- Add new customers in QuickBooks first if they don't exist in the list

### [4/6] CoS Reconciliation (Interactive)

You'll map each CoS to a PRODUCTION service item:

```
New Class of Service found: customer-50gb
Detected quota: 50 GB

Available QuickBooks items:
  0: Skip (don't map)
  1: Email Hosting - 50GB Mailbox (Current QBO price: $15.00)
  2: Email Hosting - 25GB Mailbox (Current QBO price: $10.00)

Select QBO item number [0]: 1

✓ Mapped customer-50gb to Email Hosting - 50GB Mailbox ($15.00 per mailbox)
```

### [5/6] Generating Report
```
Generating Excel billing report...
✓ Report saved: data/billing_report_2025_10_20251030_153045.xlsx
```

### [6/6] Summary
```
Billing Summary for October 2025:
  Domains processed: 87
  Billable domains: 85
  Total line items: 178
  Total amount: $8,450.00

✓ Billing run completed (no invoices created)
```

---

## Step 4.9: Review Production Report

Open and thoroughly review the Excel report:

```bash
# macOS
open data/billing_report_2025_10_*.xlsx

# Linux
xdg-open data/billing_report_2025_10_*.xlsx

# Windows
start data\billing_report_2025_10_*.xlsx
```

**Review Carefully:**
- ✅ All domains mapped to correct customers
- ✅ All CoS mapped to correct items with correct pricing
- ✅ Quantities match expected mailbox counts
- ✅ Total billing amount looks reasonable
- ✅ No unexpected domains or charges

**If anything looks wrong:**
- You can re-run reconciliation: `python3 -m src.ui.cli reconcile-domains`
- Or manually fix mappings in database before creating invoices

---

## Step 4.10: Create Production Invoices (AS DRAFTS)

Once you're satisfied with the report, create the actual invoices:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-fetch --skip-reconciliation
```

**Flags:**
- `--skip-fetch` - Use cached Zimbra data
- `--skip-reconciliation` - Use saved mappings

**Expected output:**
```
[1/6] Using cached reports... ✓
[2/6] Using cached usage data... ✓
[3/6] Using saved domain mappings... ✓
[4/6] Using saved CoS mappings... ✓
[5/6] Creating invoices in QuickBooks...
  Creating invoice for ACME Corporation... ✓
  Creating invoice for Beta Industries... ✓
  ...
  ✓ Created 85 invoices (all drafts)
[6/6] Generating report... ✓

✓ Production invoices created successfully!
```

**⚠️ IMPORTANT**: All invoices are created as **DRAFTS** - they won't be sent to customers until you manually approve and send them from QuickBooks.

---

## Step 4.11: Review Invoices in Production QuickBooks

**THIS IS CRITICAL** - Review every invoice before sending:

1. **Open Production QuickBooks**
   - Go to: https://qbo.intuit.com
   - Click **Sales** → **Invoices**

2. **Filter by Draft Status**
   - Click filter → **Status: Draft**
   - You should see all newly created invoices

3. **Review Each Invoice**
   - Open several invoices
   - Verify:
     - ✅ Correct customer
     - ✅ Correct line items (CoS descriptions)
     - ✅ Correct quantities
     - ✅ Correct pricing
     - ✅ Correct total amount
     - ✅ Invoice date is appropriate

4. **Test One Invoice** (Recommended)
   - Select one invoice for a friendly/internal customer
   - Click **"Review and Send"**
   - Send to yourself or test email
   - Verify the email and PDF look professional

5. **Send Remaining Invoices**
   - Once satisfied, you can send invoices individually or in batch
   - QuickBooks has bulk send options: **Select multiple** → **Batch actions** → **Send**

---

## Step 4.12: Verify No Duplicates

The system prevents duplicate invoices. Test this by re-running:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10
```

**Expected output:**
```
[5/6] Creating invoices in QuickBooks...
✓ Skipped 85 invoices (already exist for this period)

✓ No new invoices created
```

The system tracks which invoices were created and won't create duplicates.

---

## Step 4.13: Next Month Forward

For subsequent months, the workflow is simpler:

```bash
# Run full billing for next month
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 11
```

**What happens:**
- Fetches new Zimbra reports
- Uses existing domain/CoS mappings
- Only prompts for NEW domains or CoS types
- Creates new invoices
- Generates report

**You're now in production!** See **Step 5: Operator Guide** for monthly operations.

---

## Troubleshooting

### Wrong Company Selected

**Error**: Connected to sandbox instead of production
```bash
rm data/qbo_tokens.enc
python3 -m src.ui.cli authorize-qbo
# Select PRODUCTION company this time
```

### Database Still Has Sandbox Data

**Error**: Old sandbox customers showing up
```bash
# Re-clean database
sqlite3 data/billing.db "DELETE FROM customers; DELETE FROM domains;"
# Re-sync production customers
python3 -m src.ui.cli sync-customers
```

### Production Credentials Not Working

**Error**: Invalid client credentials
- Verify you copied PRODUCTION credentials (not Development)
- Check for extra spaces in `.env` file
- Ensure app is approved for production in developer portal

### Can't Find Production Company ID

1. Log into production QBO
2. Look at URL: `realmId=XXXXXXXXXX`
3. Copy that number to `.env` as `QBO_COMPANY_ID`

### Invoices Have Wrong Pricing

- Pricing comes from QuickBooks service items
- Update item prices in QuickBooks: Gear → Products and Services
- Re-run billing (existing invoices won't change)

---

## Summary Checklist

Before proceeding to Step 5, ensure:

- [ ] Applied for and received Production OAuth credentials
- [ ] Prepared production QuickBooks (items and customers)
- [ ] Cleaned ALL sandbox data from database
- [ ] Updated `.env` with production credentials
- [ ] Authorized with PRODUCTION QuickBooks (verified environment)
- [ ] Synced production customers
- [ ] Tested production connection
- [ ] Run test billing with --skip-invoices
- [ ] Reviewed Excel report thoroughly
- [ ] Created production invoices (as drafts)
- [ ] Reviewed all invoices in QuickBooks
- [ ] Sent test invoice to verify
- [ ] Confirmed no duplicates on re-run

---

## What's Next?

✅ **You've completed Step 4!**

You've successfully deployed to production and created your first real invoices!

**Next Step**: [5_OPERATOR_GUIDE.md](5_OPERATOR_GUIDE.md)

Step 5 provides the operational procedures for monthly billing operations, including:
- Monthly billing workflow
- Handling new domains and CoS types
- Troubleshooting common issues
- Database maintenance
- Best practices

---

## Reverting to Sandbox (If Needed)

If you ever need to test in sandbox again:

```bash
# 1. Clean production data
sqlite3 data/billing.db "DELETE FROM invoice_history; DELETE FROM customers; DELETE FROM domains; DELETE FROM cos_mappings;"

# 2. Restore sandbox config
cp .env.sandbox-backup .env

# 3. Clear production tokens
rm data/qbo_tokens.enc

# 4. Re-authorize with sandbox
python3 -m src.ui.cli authorize-qbo
# Select SANDBOX company

# 5. Sync sandbox customers
python3 -m src.ui.cli sync-customers
```

**Important**: Always clean the database when switching between environments!

---

## Production Best Practices

1. **Always Review Drafts** - Never auto-send invoices
2. **Backup Regularly** - `cp data/billing.db backups/billing_$(date +%Y%m%d).db`
3. **Monitor Logs** - Check `data/logs/` for errors
4. **Test New Months** - Use `--skip-invoices` first
5. **Keep Mappings Updated** - New domains/CoS need prompt mapping
6. **Track Token Expiration** - Re-authorize every ~100 days
7. **Document Changes** - Note any manual adjustments made

Your billing system is now live! 🎉
