#!/bin/bash
# Prepare for June 2025 invoice comparison test
# This script modifies the database to "hide" existing June 2025 invoices
# so the system can regenerate them with the new Decimal precision code.

set -e  # Exit on error

echo "======================================================================"
echo "June 2025 Invoice Comparison Test - Preparation"
echo "======================================================================"
echo ""
echo "This script will:"
echo "  1. Create a backup of your database"
echo "  2. Mark existing June 2025 invoices as 'ORIGINAL-FLOAT-VERSION'"
echo "  3. Modify their idempotency keys so they won't block new invoices"
echo ""
echo "Your QuickBooks draft invoices will NOT be touched."
echo ""
read -p "Press ENTER to continue or Ctrl+C to cancel..."

# Get the database path from config or use default
DB_PATH="${1:-data/billing.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    exit 1
fi

echo ""
echo "Step 1: Creating backup..."
BACKUP_PATH="${DB_PATH}.backup_$(date +%Y%m%d_%H%M%S)"
cp "$DB_PATH" "$BACKUP_PATH"
echo "✓ Backup created: $BACKUP_PATH"

echo ""
echo "Step 2: Checking existing June 2025 invoices..."
JUNE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM invoice_history WHERE billing_year=2025 AND billing_month=6;")
echo "✓ Found $JUNE_COUNT June 2025 invoice(s) in database"

if [ "$JUNE_COUNT" -eq 0 ]; then
    echo ""
    echo "WARNING: No June 2025 invoices found in database!"
    echo "Are you sure you created them previously?"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo "Step 3: Marking old invoices and modifying idempotency keys..."
sqlite3 "$DB_PATH" <<SQL
-- Mark existing June 2025 invoices
UPDATE invoice_history
SET notes='ORIGINAL-FLOAT-VERSION',
    idempotency_key=idempotency_key||'_OLD'
WHERE billing_year=2025 AND billing_month=6;
SQL
echo "✓ June 2025 invoices marked as old version"

echo ""
echo "Step 4: Verifying changes..."
sqlite3 "$DB_PATH" <<SQL
SELECT
    'Customer ID: ' || customer_id,
    'Invoice: ' || qbo_invoice_id,
    'Amount: $' || total_amount,
    'Marked: ' || notes
FROM invoice_history
WHERE billing_year=2025 AND billing_month=6
ORDER BY customer_id;
SQL

echo ""
echo "======================================================================"
echo "✓ Preparation Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Run: zimbra-billing run-monthly-billing --year 2025 --month 6"
echo "  2. The system will create NEW June 2025 invoices (with Decimal precision)"
echo "  3. Run: ./scripts/compare_june_invoices.sh"
echo ""
echo "If something goes wrong, restore with:"
echo "  cp $BACKUP_PATH $DB_PATH"
echo ""
