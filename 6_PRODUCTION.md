# Switching to Production QuickBooks

> 📚 **New to this application?** See **3_SETUP_GUIDE.md** for the complete journey from initial installation through sandbox testing to production deployment.

This guide focuses specifically on switching from QuickBooks Sandbox to your Production QuickBooks company.

## Overview

Currently, the application is configured to use QuickBooks **Sandbox** for testing. Before switching to production, you must clean all sandbox data from the database to avoid any contamination between test and real data.

This guide will help you:
1. Backup your current configuration
2. Clean all sandbox data from the database
3. Switch to production QuickBooks
4. Re-authorize with your production company
5. Import your real customers
6. Map all domains and CoS to production data
7. Test and verify everything works

**Time Required**: 30-60 minutes (depending on number of domains to map)

**Important**: Always clean the database when switching between sandbox and production to ensure complete separation of test and real data.

## Prerequisites

✅ You have successfully tested the application with sandbox
✅ You have a QuickBooks Online production account
✅ You have access to the QuickBooks Developer portal (for OAuth credentials)
✅ All your production customers exist in QuickBooks Online
✅ All your service items (for CoS mapping) exist in QuickBooks Online as List Items

## Step-by-Step Instructions

### 1. Backup Your Current Configuration

Before making any changes, backup your current configuration:

```bash
cd ~/zimbra-qbo-billing
cp .env .env.sandbox-backup
```

### 2. Clean All Sandbox Data

Remove all sandbox test data from the database to start fresh with production:

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
- Removes all sandbox customers and their mappings
- Clears all test invoice history
- Removes all domain and CoS mappings
- Clears all usage data from sandbox testing
- Ensures a completely clean slate for production

**Important**: This step is critical to prevent mixing sandbox and production data.

**Note**: The database schema will automatically migrate when you next run the application. If you see messages about adding an `idempotency_key` column, this is normal and expected. See `MIGRATION_GUIDE.md` for details.

### 3. Find Your Production Company ID

You need your production QuickBooks Company ID (also called Realm ID).

**Option A: From QuickBooks URL**
1. Log into your production QuickBooks Online at https://qbo.intuit.com
2. Look at the browser URL bar
3. You'll see something like: `https://app.qbo.intuit.com/app/homepage?realmId=1234567890`
4. Copy the number after `realmId=` - this is your Company ID

**Option B: Let the authorization show it**
1. The `authorize-qbo` command will display it after successful auth
2. You can use this method in step 4 below

### 4. Update Configuration

Edit your `.env` file:

```bash
nano .env
```

Change these two settings:

**Before** (Sandbox):
```
QBO_COMPANY_ID=9341455543932441
QBO_SANDBOX=true
```

**After** (Production):
```
QBO_COMPANY_ID=<your-production-company-id>
QBO_SANDBOX=false
```

Save and exit (Ctrl+O, Enter, Ctrl+X in nano).

**Important**: If you don't know your production Company ID yet, you can set `QBO_SANDBOX=false` now and set the Company ID after step 4.

### 5. Clear Sandbox Authorization

Remove the sandbox OAuth tokens and encryption key:

```bash
rm data/qbo_tokens.enc
rm data/.qbo_key
```

This forces a new authorization with production and creates a new encryption key for production tokens.

**Security Note**: Tokens are encrypted at rest using Fernet encryption. The system automatically manages encryption keys securely.

### 6. Re-Authorize with Production QuickBooks

Run the authorization command:

```bash
python3 -m src.ui.cli authorize-qbo
```

**What happens:**
1. A browser window opens
2. You'll be prompted to sign in to Intuit
3. **IMPORTANT**: Select your **PRODUCTION** company (not sandbox)
4. Click "Authorize" to grant access
5. **Complete this immediately** - don't wait or the code will expire

**After successful authorization:**
- The command will display your Company ID
- If you didn't set it in step 3, update `.env` now with this Company ID
- Tokens are saved to `data/qbo_tokens.enc`

### 7. Test the Connection

Verify the production connection works:

```bash
python3 -m src.ui.cli test-connections
```

**Expected output:**
```
Testing Zimbra SSH connection...
✓ Zimbra connection successful

Testing QuickBooks Online connection...
✓ QuickBooks connection successful
  Company: <Your Production Company Name>
```

If this fails, go back to step 5 and re-authorize.

### 8. Import Production Customers

Sync your real customers from production QuickBooks:

```bash
python3 -m src.ui.cli sync-customers
```

**What this does:**
- Fetches all active customers from your production QuickBooks
- Imports them into the local database
- Creates records for mapping domains

**Expected output:**
```
Syncing QuickBooks customers...
✓ Synced 150 customers
```

The number will vary based on how many customers you have.

### 9. View Production Customers

Optionally, view the imported customers to verify:

```bash
sqlite3 data/billing.db "SELECT id, customer_name, qbo_customer_id FROM customers ORDER BY customer_name LIMIT 20;"
```

### 10. Map Domains to Production Customers

Now you need to assign all your domains to the correct production customers. Since the database was cleaned in step 2, all domains from the Zimbra reports will need to be mapped:

```bash
python3 -m src.ui.cli reconcile-domains
```

**What happens:**
- Shows each unmapped domain
- Lists numbered customers to choose from
- You select the correct customer for each domain
- Skip domains that shouldn't be billed (enter 0)

**Example interaction:**
```
Found 87 unmapped domains

Domain: example.com
Select customer number [0 to skip]:
1. ABC Corp
2. XYZ Industries
3. Example Company
...
Select customer number [0 to skip]: 3
✓ Assigned example.com to Example Company
```

**Tips:**
- Have a list of domain-to-customer mappings ready
- You can search by typing part of the customer name
- Enter 0 to skip domains you don't recognize or want to exclude
- This process can take 15-30 minutes for ~85 domains

### 11. Verify Domain Mappings

Check how many domains are mapped:

```bash
sqlite3 data/billing.db "SELECT COUNT(*) FROM domains WHERE customer_id IS NOT NULL;"
```

### 12. Map CoS to Production Items

Now you need to map all Class of Service types to your production QuickBooks items. Since the database was cleaned in step 2, all CoS types will need to be mapped:

```bash
python3 -m src.ui.cli reconcile-cos
```

**What happens:**
- Shows each unmapped CoS type
- Lists your production QuickBooks service items
- You select the correct item for each CoS
- Confirms the unit price from the item

**Example interaction:**
```
Found 31 unmapped CoS types

CoS: customer-50gb (Quota: 50GB)
Select item number [0 to skip]:
1. Email Hosting - 50GB ($10.00)
2. Email Hosting - 100GB ($15.00)
...
Select item number [0 to skip]: 1
Unit price: $10.00
✓ Mapped customer-50gb to Email Hosting - 50GB at $10.00
```

**Tips:**
- Have your pricing structure documented
- Create items in QuickBooks first if they don't exist
- The quota size in CoS name (e.g., "50gb") helps match to items
- You can update prices later in the database if needed

### 13. Test with Existing Data (No Invoices)

Now test the billing run using your existing March 2025 data, but **without creating invoices**:

```bash
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation --skip-invoices
```

**What this does:**
- Uses the existing Zimbra reports (--skip-fetch)
- Skips reconciliation prompts (--skip-reconciliation)
- Does NOT create invoices (--skip-invoices)
- Generates an Excel report with production customer/item names

**Expected output:**
```
[5/6] Generating Excel report...
      Report saved to: data/billing_report_2025_03.xlsx

Billing Period: 2025-03
Total Customers: 50
Total Amount: $3,210.00
```

### 14. Review the Test Report

Open the Excel report and verify:

```bash
# macOS
open data/billing_report_2025_03.xlsx

# Linux
xdg-open data/billing_report_2025_03.xlsx

# Windows
start data/billing_report_2025_03.xlsx
```

**Check:**
- ✓ Customer names match your production customers
- ✓ Item descriptions match your production items
- ✓ Prices are correct
- ✓ Quantities make sense
- ✓ Totals are accurate

### 15. Preview Invoices (Optional)

Before creating real invoices, preview what would be created:

```bash
python3 -m src.ui.cli preview-invoices --year 2025 --month 3
```

This shows exactly what invoices would look like without creating them in QuickBooks.

### 16. Create Test Invoice for One Customer

Test with a single invoice first:

```bash
# Find a small customer ID from your report
sqlite3 data/billing.db "SELECT customer_id, customer_name FROM customers WHERE qbo_customer_id IN (SELECT DISTINCT qbo_customer_id FROM invoice_history) LIMIT 1;"

# Or create invoice manually (see src/qbo/invoice.py for API)
```

**Note**: The CLI doesn't currently support single-customer invoice generation. You can:
- Run the full billing and review all drafts in QBO before sending
- Or wait to create invoices until next month's run

### 17. Production Billing Run (When Ready)

When you're confident everything is correct:

```bash
# For current month's data (fetches new reports)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 10 --skip-reconciliation

# For March again (using existing data)
python3 -m src.ui.cli run-monthly-billing --year 2025 --month 3 --skip-fetch --skip-reconciliation
```

**This will**:
- Create REAL draft invoices in your production QuickBooks
- Generate the Excel report
- Display billing summary

**Important**: Invoices are created as **drafts** by default. They will NOT be sent to customers until you manually review and send them from the QuickBooks web interface.

### 18. Review Invoices in QuickBooks

1. Log into QuickBooks Online
2. Go to **Sales** → **Invoices**
3. Filter by **Draft** status
4. Review each invoice
5. Click **Save and Send** when ready

## Verification Checklist

After switching to production, verify:

- [ ] `test-connections` shows production company name
- [ ] Customer count matches your production customer count
- [ ] All active domains are mapped to correct customers
- [ ] All CoS types are mapped to correct items with correct prices
- [ ] Test report shows correct customer names and items
- [ ] Excel report totals are reasonable
- [ ] Draft invoices appear in QuickBooks Online
- [ ] Draft invoices show correct customer, items, and amounts

## Troubleshooting

### Authorization Fails

**Error**: "Authorization failed" or "Invalid client"

**Fix**:
1. Verify Client ID and Client Secret in `.env`
2. Make sure `QBO_SANDBOX=false`
3. Try authorizing in an incognito/private browser window
4. Check that redirect URI matches: `http://localhost:8080/callback`

### Wrong Company Selected

**Error**: Connected to wrong company

**Fix**:
1. `rm data/qbo_tokens.enc`
2. Run `authorize-qbo` again
3. Pay attention to company selector during auth
4. Choose the correct production company

### Customers Not Syncing

**Error**: "Synced 0 customers" or fewer than expected

**Fix**:
1. Check QuickBooks - are customers marked as inactive?
2. The sync only imports active customers
3. Activate customers in QuickBooks, then sync again

### CoS Items Don't Match

**Error**: Can't find items during CoS reconciliation

**Fix**:
1. Check that items exist in production QuickBooks
2. Go to **Sales** → **Products and Services** in QBO
3. Create missing items
4. Run `reconcile-cos` again

### Database Shows Sandbox Data

**Error**: Old sandbox customer names appearing

**Fix**:
```bash
# Clean all sandbox data (see Step 2 above)
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

# Re-sync production customers
python3 -m src.ui.cli sync-customers

# Re-run reconciliation
python3 -m src.ui.cli reconcile-domains
python3 -m src.ui.cli reconcile-cos
```

## Reverting to Sandbox

If you need to go back to sandbox for testing or troubleshooting:

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

# Or manually update .env:
# QBO_SANDBOX=true
# QBO_COMPANY_ID=9341455543932441

# 3. Clear production tokens
rm data/qbo_tokens.enc

# 4. Re-authorize with sandbox
python3 -m src.ui.cli authorize-qbo
# Select SANDBOX company during auth

# 5. Sync sandbox customers
python3 -m src.ui.cli sync-customers
```

**Important**: Always clean the database when switching back to avoid mixing production and sandbox data.

## Important Production Notes

1. **Backup Regularly**: Back up `data/billing.db` before each monthly run
   ```bash
   cp data/billing.db data/billing.db.$(date +%Y%m%d)
   ```

2. **Review Before Sending**: Always review draft invoices in QBO before sending

3. **Monitor First Month**: Watch the first production month closely to catch any issues

4. **Document Mappings**: Keep a record of which domains map to which customers

5. **Update Exclusions**: Add test/internal domains to exclusions in `.env` or `config.json`

6. **Token Expiration**: Tokens refresh automatically for 101 days, then need re-authorization

7. **Idempotency Protection**: The system now prevents duplicate invoices automatically. You can safely re-run billing for the same period without creating duplicates.

8. **SSH Security**: By default, the system uses strict host key verification. Add your Zimbra server to `~/.ssh/known_hosts` before the first run:
   ```bash
   ssh-keyscan -H your-zimbra-host.com >> ~/.ssh/known_hosts
   ```

9. **Token Security**: OAuth tokens are encrypted at rest and masked in logs. Never commit `.qbo_key` or `qbo_tokens.enc` to version control.

10. **Database Migrations**: The system automatically applies schema migrations. See `MIGRATION_GUIDE.md` for details.

## Monthly Production Workflow

Once set up, your monthly workflow will be:

### Interactive Mode (First Few Months)

```bash
# First day of month - run billing for previous month
cd ~/zimbra-qbo-billing
python3 -m src.ui.cli run-monthly-billing --skip-reconciliation

# Review Excel report (use command for your OS)
open data/billing_report_YYYY_MM.xlsx        # macOS
xdg-open data/billing_report_YYYY_MM.xlsx    # Linux
start data/billing_report_YYYY_MM.xlsx       # Windows

# Review drafts in QuickBooks Online
# https://qbo.intuit.com → Sales → Invoices → Draft

# Send invoices when ready (in QuickBooks UI)
```

### Automated Mode (Once Stable)

After your mappings are stable, automate with cron/Task Scheduler:

```bash
# Non-interactive with JSON output
python3 -m src.ui.cli run-monthly-billing \
  --non-interactive \
  --json-output /var/log/billing/summary.json

# Check JSON for any issues
cat /var/log/billing/summary.json | jq '.status'

# Manually reconcile only new items if needed
python3 -m src.ui.cli reconcile-domains
python3 -m src.ui.cli reconcile-cos
```

**Benefits of Non-Interactive Mode**:
- Safe to run in cron/scheduled tasks
- Prevents duplicate invoices automatically
- Skips unmapped items (reports them for manual review)
- Machine-readable JSON output for monitoring
- Can safely re-run if there are failures

See `5_USAGE.md` for detailed automation examples.

## Support

If you encounter issues:
1. Check logs: `tail -f data/logs/*.log`
2. Run with debug: `python3 -m src.ui.cli --debug <command>`
3. Review this guide
4. Check 5_USAGE.md for command details
5. See 3_SETUP_GUIDE.md for complete setup process

## Summary

After completing these steps, you'll have:
- ✓ Production QuickBooks connected
- ✓ Real customers imported
- ✓ Domains mapped to customers
- ✓ CoS mapped to items with pricing
- ✓ Ability to generate real invoices
- ✓ Automated monthly billing ready

**Ready to start?** Begin with Step 1: Backup your data.
