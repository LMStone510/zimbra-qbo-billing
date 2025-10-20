# Zimbra-to-QuickBooks Billing Automation - Project Summary

## Implementation Status

✅ **All 6 phases implemented and tested**
✅ **Successfully tested with QuickBooks Sandbox**
✅ **Ready for production deployment**

### Test Results (March 2025)
- Fetched 6 weekly reports from Zimbra
- Parsed 87 domains with usage data
- Calculated 151 highwater marks
- Mapped 85 domains to customers
- Mapped 31 CoS types to QuickBooks items
- Generated 69 billable line items
- Total billing: **$3,210.00**
- Excel report generated successfully

## Project Structure

```
invoicing/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main application orchestration
│   ├── config.py               # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy database models
│   │   ├── migrations.py      # Database initialization
│   │   └── queries.py         # Database query helpers
│   ├── zimbra/
│   │   ├── __init__.py
│   │   ├── fetcher.py         # SSH/SCP report fetching
│   │   ├── parser.py          # Report parsing
│   │   └── calculator.py      # High-water mark calculations
│   ├── qbo/
│   │   ├── __init__.py
│   │   ├── auth.py            # OAuth2 authentication
│   │   ├── client.py          # QBO API client wrapper
│   │   └── invoice.py         # Invoice generation
│   ├── reconciliation/
│   │   ├── __init__.py
│   │   ├── detector.py        # Change detection
│   │   ├── prompter.py        # User interaction prompts
│   │   └── mapper.py          # Domain/CoS/Customer mapping
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── excel.py           # Excel report generation
│   └── ui/
│       ├── __init__.py
│       └── cli.py             # Command-line interface
├── data/
│   ├── config.json.example    # Example configuration
│   └── logs/                  # Application logs
├── tests/
│   ├── test_parser.py
│   ├── generate_sample_data.py
│   └── sample_data/           # Test data files
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── README.md                  # Project overview
├── USAGE.md                   # Detailed usage guide
└── .gitignore

```

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

## Key Capabilities

1. **Automated Report Fetching** - SSH into Zimbra server and download reports
2. **Intelligent Parsing** - Extract domains, CoS, and account counts
3. **High-water Billing** - Calculate maximum monthly usage per domain/CoS
4. **Smart Reconciliation** - Detect and handle new/missing domains and CoS
5. **QBO Integration** - Create draft invoices with proper line items
6. **Excel Reporting** - Professional multi-sheet billing reports
7. **Audit Trail** - Complete change log and history tracking
8. **Exclusion Patterns** - Flexible filtering of non-billable items

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

## CLI Commands

### Main Commands
- `run-monthly-billing` - Complete monthly workflow
- `generate-report` - Excel report only
- `preview-invoices` - Preview without creating
- `reconcile-domains` - Assign domains to customers
- `reconcile-cos` - Map CoS to QBO items

### Setup Commands
- `init-db` - Initialize database
- `authorize-qbo` - QBO OAuth authorization
- `sync-customers` - Import QBO customers
- `test-connections` - Verify connectivity

## Quick Start

1. **Install**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp data/config.json.example data/config.json
   # Edit config.json with your credentials
   ```

3. **Initialize**
   ```bash
   python -m src.ui.cli init-db
   python -m src.ui.cli authorize-qbo
   python -m src.ui.cli sync-customers
   ```

4. **Run First Billing**
   ```bash
   python -m src.ui.cli run-monthly-billing --year 2025 --month 10
   ```

## Testing

Sample test files included:
- `tests/test_parser.py` - Unit tests for parser
- `tests/generate_sample_data.py` - Generate test reports

Generate sample data:
```bash
python tests/generate_sample_data.py 2025 10
```

## Security

- OAuth2 tokens encrypted at rest (Fernet encryption)
- SSH key-based authentication for Zimbra
- Restrictive file permissions on sensitive data
- No credentials in code or logs
- Environment variable support for secrets

## Error Handling

- Comprehensive exception handling throughout
- Graceful degradation (continue on single failures)
- Detailed logging with debug mode
- Transaction rollback on errors
- User-friendly error messages

## Extensibility

The modular design allows easy extension:
- Add new report formats (extend parser)
- Support additional billing rules (modify calculator)
- Integrate other accounting systems (follow QBO pattern)
- Add web UI (import main workflow functions)

## Documentation

- `1_README.md` - Project overview
- `2_SETUP_GUIDE.md` - Complete setup guide from sandbox to production
- `3_QUICKSTART.md` - Quick reference
- `4_USAGE.md` - Detailed usage guide with examples
- `5_PRODUCTION.md` - Production-specific setup
- `6_PROJECT_SUMMARY.md` - This file (technical architecture)
- Inline code documentation throughout

## Next Steps

1. Configure with your actual credentials
2. Test Zimbra and QBO connections
3. Perform initial domain/CoS reconciliation
4. Run first billing cycle
5. Review generated invoices and reports
6. Set up monthly automation (cron/launchd)

## Architecture Highlights

- **Separation of Concerns** - Clear module boundaries
- **Database-Driven** - All state in SQLite
- **Interactive Where Needed** - Prompts for important decisions
- **Automation-Friendly** - Can run fully unattended
- **Audit Trail** - Complete history of all operations
- **Production Ready** - Error handling, logging, testing

## Dependencies

- `paramiko` - SSH/SCP for Zimbra
- `sqlalchemy` - Database ORM
- `python-quickbooks` - QBO API
- `openpyxl` - Excel generation
- `click` - CLI framework
- `cryptography` - Token encryption
- `requests-oauthlib` - OAuth2

## Support

For questions or issues:
1. Check 2_SETUP_GUIDE.md for complete setup process
2. Check 4_USAGE.md for common tasks
3. Review logs in data/logs/
4. Use --debug flag for verbose output
5. Check configuration in .env and data/config.json

## License

MIT License - Open source and free to use

Copyright 2025 Mission Critical Email LLC

This software is provided "AS IS" without warranty of any kind. See the LICENSE file for full details.

**For Zimbra Partners**: This application is open source and available for use by other Zimbra partners and users. Contributions and improvements are welcome!

---

**Status**: ✅ All phases complete and ready for deployment!
