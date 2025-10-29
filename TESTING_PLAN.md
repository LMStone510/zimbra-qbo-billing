# June 2025 Invoice Comparison Test Plan

## Purpose
Validate that the Decimal precision fixes work correctly by comparing invoices generated with the old (float) code vs new (Decimal) code.

## What This Tests
- ✅ End-to-end billing workflow still functions
- ✅ Decimal precision improvements are measurable
- ✅ System produces correct invoices with real data

## Prerequisites
- You have June 2025 draft invoices in QuickBooks (created with old float code)
- These invoices are still in DRAFT status in QuickBooks
- Your database has records of these invoices

## Step-by-Step Instructions

### Step 1: Prepare the Database (2 minutes)

Run the preparation script:
```bash
cd ~/claude-dir/invoicing
./scripts/prepare_june_retest.sh
```

**What this does:**
- Creates a timestamped backup of your database
- Marks existing June 2025 invoices as "ORIGINAL-FLOAT-VERSION"
- Modifies their idempotency keys so the system can create new ones
- **Does NOT touch your QuickBooks drafts**

**Output:** You'll see a summary of how many June 2025 invoices were found and marked.

---

### Step 2: Run June 2025 Billing (5-10 minutes)

Generate NEW June 2025 invoices with Decimal precision:
```bash
zimbra-billing run-monthly-billing --year 2025 --month 6
```

**What this does:**
- Fetches Zimbra usage data (or uses cached data)
- Calculates high-water marks
- Creates NEW draft invoices in QuickBooks
- Uses Decimal precision for all money calculations

**Expected output:**
- Should create the same number of invoices as before
- All amounts calculated with Decimal precision
- Excel report generated

---

### Step 3: Compare Results (1 minute)

Run the comparison script:
```bash
./scripts/compare_june_invoices.sh
```

**What this does:**
- Compares old (float) vs new (Decimal) invoice amounts
- Shows side-by-side comparison
- Calculates differences
- Generates summary statistics

**Expected output:**
```
====================================================================
June 2025 Invoice Comparison Report
====================================================================

Old invoices (float):    21
New invoices (Decimal):  21

====================================================================
Side-by-Side Comparison
====================================================================

Customer      Old_Invoice  New_Invoice  Old_Amount   New_Amount   Difference
------------  -----------  -----------  -----------  -----------  ----------
ACME Corp     INV-1001     INV-2001     $1,234.56    $1,234.57    $0.01
Widget Inc    INV-1002     INV-2002     $567.89      $567.89      $0.00
...

====================================================================
Summary Statistics
====================================================================

Total_Compared  Identical  Different  Old_Total     New_Total     Total_Diff
--------------  ---------  ---------  ------------  ------------  ----------
21              18         3          $12,345.67    $12,345.70    $0.03
```

---

### Step 4: Review in QuickBooks (5 minutes)

**In QuickBooks:**
1. Go to Sales → Invoices
2. Filter for June 2025 invoices
3. You'll see TWO sets of draft invoices:
   - **Old set**: Created with float calculations
   - **New set**: Just created with Decimal precision

**Compare a few manually:**
- Pick invoices that show differences in the report
- Verify amounts match what the script reported
- Check line items if you want to see where differences came from

---

### Step 5: Clean Up (2 minutes)

#### In QuickBooks:
Delete the OLD draft invoices (you can identify them by creation date or cross-reference with the old Invoice IDs from the report).

#### In Database:
Remove old invoice records:
```bash
sqlite3 data/billing.db "DELETE FROM invoice_history WHERE notes='ORIGINAL-FLOAT-VERSION';"
```

Or keep them for historical record (they won't interfere).

---

## What to Expect

### Best Case: Some Differences
- 2-5 invoices show penny differences ($0.01-$0.03)
- Confirms floating-point rounding was an issue
- Validates that Decimal fix made a real difference

### Also Good: No Differences
- All invoices match exactly
- Means your specific usage data didn't trigger float rounding issues
- But the Decimal fix prevents potential issues with different data

### Red Flag: Large Differences
- If any invoice differs by > $0.10
- **Stop and investigate** - something unexpected happened
- Contact support/review logs

---

## Rollback Plan

If anything goes wrong:

### Restore Database:
```bash
# Find your backup
ls -lt data/billing.db.backup_*

# Restore it
cp data/billing.db.backup_YYYYMMDD_HHMMSS data/billing.db
```

### Delete New Invoices in QuickBooks:
Delete the newly created draft invoices (by date).

---

## Success Criteria

✅ Same number of invoices created (old count = new count)
✅ Most/all amounts match exactly or differ by pennies
✅ No system errors during invoice creation
✅ Excel report generated successfully
✅ All new invoices appear in QuickBooks as drafts

---

## Questions?

If you encounter issues:
1. Check the logs: `data/logs/`
2. Review the backup: `data/billing.db.backup_*`
3. Don't delete anything in QuickBooks until you're satisfied

---

**Ready to start? Run:** `./scripts/prepare_june_retest.sh`
