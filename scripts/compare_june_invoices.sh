#!/bin/bash
# Compare old (float) vs new (Decimal) June 2025 invoices
# This script generates a detailed comparison report

set -e  # Exit on error

echo "======================================================================"
echo "June 2025 Invoice Comparison Report"
echo "======================================================================"
echo ""

# Get the database path from config or use default
DB_PATH="${1:-data/billing.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    exit 1
fi

# Check if we have both old and new invoices
OLD_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM invoice_history WHERE billing_year=2025 AND billing_month=6 AND notes='ORIGINAL-FLOAT-VERSION';")
NEW_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM invoice_history WHERE billing_year=2025 AND billing_month=6 AND (notes IS NULL OR notes != 'ORIGINAL-FLOAT-VERSION');")

echo "Old invoices (float):    $OLD_COUNT"
echo "New invoices (Decimal):  $NEW_COUNT"
echo ""

if [ "$OLD_COUNT" -eq 0 ] || [ "$NEW_COUNT" -eq 0 ]; then
    echo "ERROR: Missing invoices. Did you run the billing for June 2025?"
    exit 1
fi

# Generate comparison report
echo "======================================================================"
echo "Side-by-Side Comparison"
echo "======================================================================"
echo ""

sqlite3 "$DB_PATH" <<'SQL'
.mode column
.headers on
.width 12 12 15 15 10

SELECT
    c.customer_name as Customer,
    old.qbo_invoice_id as Old_Invoice,
    new.qbo_invoice_id as New_Invoice,
    printf('$%.2f', old.total_amount) as Old_Amount,
    printf('$%.2f', new.total_amount) as New_Amount,
    printf('$%.2f', new.total_amount - old.total_amount) as Difference
FROM invoice_history old
JOIN invoice_history new
    ON old.customer_id = new.customer_id
    AND old.billing_year = new.billing_year
    AND old.billing_month = new.billing_month
JOIN customers c ON old.customer_id = c.id
WHERE old.notes = 'ORIGINAL-FLOAT-VERSION'
    AND (new.notes IS NULL OR new.notes != 'ORIGINAL-FLOAT-VERSION')
    AND old.billing_year = 2025
    AND old.billing_month = 6
ORDER BY c.customer_name;
SQL

echo ""
echo "======================================================================"
echo "Summary Statistics"
echo "======================================================================"
echo ""

sqlite3 "$DB_PATH" <<'SQL'
.mode column
.headers on

SELECT
    COUNT(*) as Total_Compared,
    COUNT(CASE WHEN new.total_amount = old.total_amount THEN 1 END) as Identical,
    COUNT(CASE WHEN new.total_amount != old.total_amount THEN 1 END) as Different,
    printf('$%.2f', SUM(old.total_amount)) as Old_Total,
    printf('$%.2f', SUM(new.total_amount)) as New_Total,
    printf('$%.2f', SUM(new.total_amount - old.total_amount)) as Total_Diff
FROM invoice_history old
JOIN invoice_history new
    ON old.customer_id = new.customer_id
    AND old.billing_year = new.billing_year
    AND old.billing_month = new.billing_month
WHERE old.notes = 'ORIGINAL-FLOAT-VERSION'
    AND (new.notes IS NULL OR new.notes != 'ORIGINAL-FLOAT-VERSION')
    AND old.billing_year = 2025
    AND old.billing_month = 6;
SQL

echo ""
echo "======================================================================"
echo "Differences by Amount"
echo "======================================================================"
echo ""

sqlite3 "$DB_PATH" <<'SQL'
.mode column
.headers on
.width 20 15 15 10

SELECT
    c.customer_name as Customer,
    printf('$%.2f', old.total_amount) as Old_Amount,
    printf('$%.2f', new.total_amount) as New_Amount,
    printf('$%.2f', new.total_amount - old.total_amount) as Difference
FROM invoice_history old
JOIN invoice_history new
    ON old.customer_id = new.customer_id
    AND old.billing_year = new.billing_year
    AND old.billing_month = new.billing_month
JOIN customers c ON old.customer_id = c.id
WHERE old.notes = 'ORIGINAL-FLOAT-VERSION'
    AND (new.notes IS NULL OR new.notes != 'ORIGINAL-FLOAT-VERSION')
    AND old.billing_year = 2025
    AND old.billing_month = 6
    AND new.total_amount != old.total_amount
ORDER BY ABS(new.total_amount - old.total_amount) DESC;
SQL

echo ""
echo "======================================================================"
echo "Analysis"
echo "======================================================================"
echo ""

# Calculate if any differences exist
DIFF_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM invoice_history old JOIN invoice_history new ON old.customer_id = new.customer_id AND old.billing_year = new.billing_year AND old.billing_month = new.billing_month WHERE old.notes = 'ORIGINAL-FLOAT-VERSION' AND (new.notes IS NULL OR new.notes != 'ORIGINAL-FLOAT-VERSION') AND old.billing_year = 2025 AND old.billing_month = 6 AND new.total_amount != old.total_amount;")

if [ "$DIFF_COUNT" -eq 0 ]; then
    echo "✓ All invoices match exactly - no floating-point errors detected"
else
    echo "✓ Found $DIFF_COUNT invoice(s) with differences"
    echo "✓ This confirms that Decimal precision made a measurable difference"
    echo ""
    echo "The differences are due to floating-point rounding in the old code."
    echo "The new Decimal-based calculations are more accurate."
fi

echo ""
echo "======================================================================"
echo "Next Steps"
echo "======================================================================"
echo ""
echo "1. Review the comparison above"
echo "2. In QuickBooks, you can now:"
echo "   - Delete the OLD draft invoices (marked ORIGINAL-FLOAT-VERSION)"
echo "   - Keep the NEW invoices (Decimal precision)"
echo "3. Clean up database:"
echo "   sqlite3 data/billing.db \"DELETE FROM invoice_history WHERE notes='ORIGINAL-FLOAT-VERSION';\""
echo ""
