# Zimbra-to-QuickBooks Billing Automation

**Version**: v1.13.0

**Status**: ✅ Production-ready, tested with QuickBooks Sandbox and used in production at Mission Critical Email

Welcome! This is an automated monthly billing system for Zimbra BSPs (Bulk Service Providers) using QuickBooks Online.

## What This Does

Automates the entire monthly billing process:

1. **Fetches** weekly usage reports from your Zimbra server (via SSH)
2. **Calculates** monthly high-water marks per domain and Class of Service
3. **Maps** domains to QuickBooks customers automatically
4. **Creates** draft invoices in QuickBooks Online
5. **Generates** Excel reports for your records

All you need to do is review and send the invoices from QuickBooks!

## Our Approach: Class of Service Based Pricing

We bill based on **Classes of Service** (CoS) - each Zimbra CoS (e.g., "2GB Mailbox", "50GB Mailbox") maps to a QuickBooks service item with its own price. The system calculates the maximum mailboxes per domain/CoS during the month (high-water mark) and bills accordingly.

## System Requirements

- **Billing Application**: Python 3.8+ (runs on macOS, Linux, or Windows)
- **Zimbra Server**: Linux (for usage report generation)
- **QuickBooks**: QuickBooks Online account

## 🚀 Getting Started: The 5-Step Journey

Follow these steps to get from zero to production:

### **[Step 1: QuickBooks Developer Setup](1_QBO_DEVELOPER_SETUP.md)** ⏱️ 30-45 min
Register for an Intuit Developer account, create an application, and set up a QuickBooks Sandbox company for testing.

### **[Step 2: Zimbra Server Setup](2_ZIMBRA_SERVER_SETUP.md)** ⏱️ 20-30 min
Install the usage report script on your Zimbra mailbox server to generate weekly billing data.

### **[Step 3: Application Deployment](3_APPLICATION_DEPLOYMENT.md)** ⏱️ 1-2 hours
Deploy the billing application on your workstation and test the complete workflow with QuickBooks Sandbox.

### **[Step 4: Production Deployment](4_PRODUCTION_DEPLOYMENT.md)** ⏱️ 1-2 hours
Get Production OAuth credentials, clean sandbox data, switch to your production QuickBooks, and create your first real invoices.

### **[Step 5: Operator Guide](5_OPERATOR_GUIDE.md)** 📖 Reference
Learn the monthly billing workflow and operational procedures for ongoing production use.

---

## 📚 Additional Documentation

- **[PROJECT_REFERENCE.md](PROJECT_REFERENCE.md)** - Complete technical reference (architecture, features, commands)
- **[5_USAGE.md](5_USAGE.md)** - Detailed command reference and usage examples
- **[99_CODE_AUDIT.md](99_CODE_AUDIT.md)** - Code quality and security audit report

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Mission Critical Email LLC. All rights reserved.

## For Zimbra Partners

This application is open source and free to use, modify, and distribute for other Zimbra partners and users. Contributions are welcome!

## Contributing

If you find any issues or have suggestions for improvement, please open an issue on GitHub.

Be kind; pay it forward.

---

**L. Mark Stone**
Mark.Stone@MissionCriticalEmail.com
Mission Critical Email, LLC
October 2025
