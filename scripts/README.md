# Zimbra Server Scripts

This directory contains scripts that run on your Zimbra mailbox server(s).

## Files

### MonthlyBillingByDomain-v6.sh

**Purpose**: Generates weekly usage reports showing mailbox counts by domain and Class of Service.

**Location on Zimbra server**: `/opt/zimbra/MonthlyBillingByDomain-v6.sh`

**Output**: Writes to `/opt/MonthlyUsageReports/MailboxUsage_YYYY-MM-DD.txt`

**Schedule**: Runs via cron on the 7th, 14th, 21st, and 28th of each month at 3:00 AM

**What it does**:
1. Queries Zimbra LDAP for all local domains
2. For each domain, gets all accounts (excluding spam/ham/virus/galsync)
3. Determines the Class of Service (CoS) for each account
4. Counts accounts per CoS per domain
5. Outputs formatted report

**Output format**:
```
------------------------------------------------------------
| Zimbra Mailbox Usage Report for 2025-03-07
------------------------------------------------------------
------------------------------------------------------------
| CoS Usage for domain1.com:
------------------------------------------------------------
- customer-50gb: 10
- customer-2gb: 5
------------------------------------------------------------

------------------------------------------------------------
| CoS Usage for domain2.com:
------------------------------------------------------------
- customer-50gb: 3
------------------------------------------------------------
```

## Installation

See **ZIMBRA_SERVER_SETUP.md** in the project root for complete installation instructions.

### Quick Install

```bash
# Copy script to Zimbra server
scp MonthlyBillingByDomain-v6.sh root@your-zimbra-server:/opt/zimbra/

# On Zimbra server, set permissions
sudo chown zimbra:zimbra /opt/zimbra/MonthlyBillingByDomain-v6.sh
sudo chmod 755 /opt/zimbra/MonthlyBillingByDomain-v6.sh

# Create output directory
sudo mkdir -p /opt/MonthlyUsageReports
sudo chown zimbra:zimbra /opt/MonthlyUsageReports
sudo chmod 744 /opt/MonthlyUsageReports

# Add to zimbra crontab
sudo su - zimbra
crontab -e
# (Add the cron lines from ZIMBRA_SERVER_SETUP.md)
```

## Testing

Run manually to test:

```bash
# On Zimbra server, as zimbra user
/opt/zimbra/MonthlyBillingByDomain-v6.sh

# View output
ls -lh /opt/MonthlyUsageReports/
cat /opt/MonthlyUsageReports/MailboxUsage_*.txt
```

## Troubleshooting

### Script not found
- Verify file is at `/opt/zimbra/MonthlyBillingByDomain-v6.sh`
- Check permissions: `ls -l /opt/zimbra/MonthlyBillingByDomain-v6.sh`

### Permission denied
- Ensure ownership: `sudo chown zimbra:zimbra /opt/zimbra/MonthlyBillingByDomain-v6.sh`
- Ensure executable: `sudo chmod 755 /opt/zimbra/MonthlyBillingByDomain-v6.sh`

### Empty output
- Verify Zimbra is running: `zmcontrol status`
- Check domains exist: `zmprov gad`
- Run script with bash -x for debugging: `bash -x /opt/zimbra/MonthlyBillingByDomain-v6.sh`

### LDAP errors
- Verify LDAP credentials are configured
- Check Zimbra LDAP is running: `zmcontrol status ldap`

## Support

For complete setup instructions and troubleshooting, see:
- **ZIMBRA_SERVER_SETUP.md** - Full installation guide
- **2_SETUP_GUIDE.md** - Complete system setup

## License

Copyright 2025 Mission Critical Email LLC. All rights reserved.

Licensed under the MIT License. See LICENSE file in the project root.
