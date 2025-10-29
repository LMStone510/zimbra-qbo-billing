# Database Migration Guide

This document describes database schema changes and how to migrate existing databases.

## Automatic Migrations

The system automatically applies migrations when you run any CLI command. The migration system is safe and non-destructive:

```bash
# Migrations run automatically on any command
python -m src.ui.cli run-monthly-billing --year 2025 --month 9
```

## Migration History

### Migration 1: Add Idempotency Key (v0.9.0 → v0.10.0)

**Date**: 2025-01-20
**Purpose**: Add idempotency support to prevent duplicate invoice creation

#### Changes

Adds `idempotency_key` column to the `invoice_history` table:

```sql
ALTER TABLE invoice_history
ADD COLUMN idempotency_key VARCHAR(255);

CREATE UNIQUE INDEX idx_invoice_idempotency
ON invoice_history(idempotency_key);
```

#### What It Does

- Allows the system to detect if an invoice has already been created for a specific customer/period
- Prevents duplicate invoices when re-running the same billing period
- Safe to apply to existing databases (column is nullable for existing records)

#### Migration Code

The migration is automatically applied by the `DatabaseManager.apply_migrations()` method in `src/database/migrations.py`:

```python
def apply_migrations(self) -> None:
    """Apply database schema migrations."""
    logger.info("Checking for database migrations...")

    inspector = inspect(self.engine)

    # Migration 1: Add idempotency_key to invoice_history
    if 'invoice_history' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('invoice_history')]
        if 'idempotency_key' not in columns:
            logger.info("Applying migration: Adding idempotency_key to invoice_history")
            with self.engine.connect() as conn:
                # Add the column (nullable for existing records)
                conn.execute('ALTER TABLE invoice_history ADD COLUMN idempotency_key VARCHAR(255)')
                # Create index
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_idempotency ON invoice_history(idempotency_key)')
                conn.commit()
            logger.info("Migration applied successfully")

    logger.info("All migrations complete")
```

#### Manual Migration (If Needed)

If you need to apply the migration manually:

```bash
# Using Python
python3 << EOF
from src.database.migrations import get_db_manager
db_manager = get_db_manager()
db_manager.apply_migrations()
EOF

# Or using SQLite directly
sqlite3 ~/.config/zimbra-qbo/billing.db << EOF
ALTER TABLE invoice_history ADD COLUMN idempotency_key VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_idempotency ON invoice_history(idempotency_key);
EOF
```

#### Verification

To verify the migration was applied:

```bash
sqlite3 ~/.config/zimbra-qbo/billing.db << EOF
.schema invoice_history
EOF
```

You should see the `idempotency_key` column in the output:

```sql
CREATE TABLE invoice_history (
    id INTEGER NOT NULL,
    qbo_invoice_id VARCHAR(50) NOT NULL,
    customer_id INTEGER NOT NULL,
    billing_year INTEGER NOT NULL,
    billing_month INTEGER NOT NULL,
    invoice_date DATETIME NOT NULL,
    total_amount FLOAT NOT NULL,
    line_items_count INTEGER,
    status VARCHAR(20),
    idempotency_key VARCHAR(255),  -- <-- This column should be present
    created_at DATETIME,
    updated_at DATETIME,
    notes TEXT,
    PRIMARY KEY (id),
    UNIQUE (qbo_invoice_id),
    UNIQUE (idempotency_key),
    FOREIGN KEY(customer_id) REFERENCES customers (id)
);
```

## Backup Before Migration

The system automatically backs up your database, but you can create manual backups:

```python
from src.database.migrations import get_db_manager

db_manager = get_db_manager()
backup_path = db_manager.backup_database()
print(f"Database backed up to: {backup_path}")
```

Or manually:

```bash
cp ~/.config/zimbra-qbo/billing.db ~/.config/zimbra-qbo/billing.db.backup
```

## Rollback

If you need to rollback a migration (not typically needed):

```bash
# Restore from backup
cp ~/.config/zimbra-qbo/billing.db.backup ~/.config/zimbra-qbo/billing.db

# Or remove just the idempotency column
sqlite3 ~/.config/zimbra-qbo/billing.db << EOF
-- SQLite doesn't support DROP COLUMN directly, need to recreate table
-- This is complex and generally not recommended
-- Better to restore from backup
EOF
```

## Future Migrations

Future schema changes will be added here with similar documentation and automatic migration support.

## Troubleshooting

### Migration Fails

If a migration fails:

1. Check the logs for specific error messages
2. Verify database file permissions: `ls -la ~/.config/zimbra-qbo/`
3. Ensure no other process is using the database
4. Try manual migration using the SQL commands above
5. Restore from backup if needed

### Migration Already Applied

The system checks if a migration is already applied before running it. You'll see:

```
INFO: All migrations complete
```

This is normal and means your database is up to date.

### Column Already Exists

If you see an error about a column already existing, the migration may have been partially applied. The system should handle this gracefully, but you can check manually:

```bash
sqlite3 ~/.config/zimbra-qbo/billing.db "PRAGMA table_info(invoice_history);"
```

## Support

For migration issues, please report at: https://github.com/LMStone510/zimbra-qbo-billing/issues
