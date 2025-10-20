# Zimbra Server Setup

This document describes how to set up the Zimbra mailbox server to generate weekly usage reports for billing.

## Overview

The billing system requires weekly usage reports from your Zimbra server. These reports are generated automatically by a script running on the Zimbra mailbox server.

**What gets generated:**
- Weekly reports showing mailbox counts by domain and Class of Service (CoS)
- Reports are saved to `/opt/MonthlyUsageReports/`
- Reports run on the 7th, 14th, 21st, and 28th of each month at 3:00 AM

## Prerequisites

- ✅ Zimbra mailbox server with root or sudo access
- ✅ `MonthlyBillingByDomain-v6.sh` script (included in this repository)
- ✅ Cron access for the `zimbra` user

## Installation Steps

### Step 1: Copy the Script to Zimbra Server

Copy `MonthlyBillingByDomain-v6.sh` from this repository to your Zimbra server:

```bash
# On your local machine (where you cloned this repo)
scp scripts/MonthlyBillingByDomain-v6.sh root@your-zimbra-server:/opt/zimbra/

# Or if using a jump host
scp scripts/MonthlyBillingByDomain-v6.sh your-user@your-zimbra-server:/tmp/
```

Then on the Zimbra server:

```bash
# Move to zimbra directory
sudo mv /tmp/MonthlyBillingByDomain-v6.sh /opt/zimbra/

# Set ownership
sudo chown zimbra:zimbra /opt/zimbra/MonthlyBillingByDomain-v6.sh

# Make executable
sudo chmod 755 /opt/zimbra/MonthlyBillingByDomain-v6.sh
```

### Step 2: Create Reports Directory

```bash
# Create directory
sudo mkdir -p /opt/MonthlyUsageReports

# Set ownership to zimbra user
sudo chown zimbra:zimbra /opt/MonthlyUsageReports

# Set permissions (rwxr--r--)
sudo chmod 744 /opt/MonthlyUsageReports
```

**Permissions breakdown:**
- `7` (owner: zimbra) - read, write, execute
- `4` (group) - read only
- `4` (others) - read only

### Step 3: Add Cron Jobs

Add the cron jobs to generate reports weekly:

```bash
# Switch to zimbra user
sudo su - zimbra

# Edit zimbra's crontab
crontab -e
```

**Add these lines at the end:**

```cron
# Generate Monthly Mailbox Usage Reports
0 3 7 * * /opt/zimbra/MonthlyBillingByDomain-v6.sh >> /opt/MonthlyUsageReports/MailboxUsage_$(date +\%Y-\%m-\%d).txt 2>&1
0 3 14 * * /opt/zimbra/MonthlyBillingByDomain-v6.sh >> /opt/MonthlyUsageReports/MailboxUsage_$(date +\%Y-\%m-\%d).txt 2>&1
0 3 21 * * /opt/zimbra/MonthlyBillingByDomain-v6.sh >> /opt/MonthlyUsageReports/MailboxUsage_$(date +\%Y-\%m-\%d).txt 2>&1
0 3 28 * * /opt/zimbra/MonthlyBillingByDomain-v6.sh >> /opt/MonthlyUsageReports/MailboxUsage_$(date +\%Y-\%m-\%d).txt 2>&1
```

**Save and exit:**
- vim/vi: Press `ESC`, then type `:wq` and press Enter
- nano: Press `Ctrl+O`, Enter, then `Ctrl+X`

**Verify cron was added:**

```bash
crontab -l | grep -A 4 "Monthly Mailbox"
```

### Step 4: Test the Script

Run the script manually to verify it works:

```bash
# As zimbra user
/opt/zimbra/MonthlyBillingByDomain-v6.sh

# Check the output
ls -lh /opt/MonthlyUsageReports/
```

You should see output showing domains and their mailbox counts by CoS.

### Step 5: Verify Reports Are Generated

After the first scheduled run (or after manual test), verify the report format:

```bash
# View the latest report
cat /opt/MonthlyUsageReports/MailboxUsage_*.txt | less
```

**Expected format:**

```
| CoS Usage for domain1.com:
- customer-50gb: 10
- customer-2gb: 5

| CoS Usage for domain2.com:
- customer-50gb: 3
```

## Cron Schedule Explained

The reports run **4 times per month**:

| Day | Time | Description |
|-----|------|-------------|
| 7th | 3:00 AM | Week 1 snapshot |
| 14th | 3:00 AM | Week 2 snapshot |
| 21st | 3:00 AM | Week 3 snapshot |
| 28th | 3:00 AM | Week 4 snapshot |

**Why these dates?**
- Captures weekly snapshots throughout the month
- 28th is the last day in all months (accounts for February)
- Billing system calculates the **high-water mark** from these snapshots

## SSH Access Setup

The billing application needs SSH access to fetch these reports. Set up key-based authentication:

### On Your Billing Server

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "billing-system"

# Copy public key to Zimbra server
ssh-copy-id zimbra@your-zimbra-server

# Or if you need to use a specific user
ssh-copy-id your-user@your-zimbra-server
```

### Test SSH Access

```bash
# Test connection
ssh zimbra@your-zimbra-server ls -l /opt/MonthlyUsageReports/

# Or with specific user
ssh your-user@your-zimbra-server ls -l /opt/MonthlyUsageReports/
```

You should be able to connect without a password prompt.

## File Permissions Summary

| Path | Owner | Permissions | Description |
|------|-------|-------------|-------------|
| `/opt/zimbra/MonthlyBillingByDomain-v6.sh` | zimbra:zimbra | 755 (rwxr-xr-x) | Executable script |
| `/opt/MonthlyUsageReports/` | zimbra:zimbra | 744 (rwxr--r--) | Reports directory |
| `/opt/MonthlyUsageReports/MailboxUsage_*.txt` | zimbra:zimbra | 644 (rw-r--r--) | Report files |

## Troubleshooting

### Reports Not Being Generated

**Check cron is running:**
```bash
# As root
systemctl status cron

# Or on older systems
service cron status
```

**Check zimbra crontab:**
```bash
# As zimbra user
crontab -l
```

**Check cron logs:**
```bash
# As root
grep CRON /var/log/syslog | grep MonthlyBilling

# Or on RHEL/CentOS
grep CRON /var/log/cron | grep MonthlyBilling
```

### Permission Denied Errors

**If script can't write to reports directory:**
```bash
sudo chown zimbra:zimbra /opt/MonthlyUsageReports
sudo chmod 744 /opt/MonthlyUsageReports
```

**If script is not executable:**
```bash
sudo chmod 755 /opt/zimbra/MonthlyBillingByDomain-v6.sh
```

### SSH Connection Issues

**From billing server, test:**
```bash
# Test basic connection
ssh zimbra@your-zimbra-server echo "Connection works"

# Test access to reports
ssh zimbra@your-zimbra-server ls /opt/MonthlyUsageReports/
```

**If using non-standard SSH port:**
Update `.env` file on billing server:
```bash
ZIMBRA_SSH_PORT=2222  # Add this if using non-standard port
```

### Script Errors

**Run script manually with verbose output:**
```bash
# As zimbra user
bash -x /opt/zimbra/MonthlyBillingByDomain-v6.sh
```

**Check Zimbra is running:**
```bash
# As zimbra user
zmcontrol status
```

### Empty Reports

**If reports are empty, check:**
1. Zimbra has domains configured: `zmprov gad`
2. Domains have mailboxes: `zmprov gqu $(zmprov gad | head -1)`
3. Script has correct permissions
4. Script output isn't going to /dev/null

## Report Cleanup

Old reports accumulate over time. Set up automatic cleanup:

```bash
# As zimbra user, edit crontab
crontab -e

# Add monthly cleanup (keeps last 90 days)
0 4 1 * * find /opt/MonthlyUsageReports/ -name "MailboxUsage_*.txt" -mtime +90 -delete
```

This removes reports older than 90 days on the 1st of each month at 4:00 AM.

## Multiple Zimbra Servers

If you have multiple Zimbra mailbox servers:

**Option 1: Run script on each server**
- Set up the script on each mailbox server
- Use different output directories (e.g., `/opt/MonthlyUsageReports-server1/`)
- Configure billing system to fetch from all servers

**Option 2: Consolidate on one server**
- Run script on one server
- Have that server query other servers remotely
- May require additional LDAP or SOAP API configuration

## Security Notes

1. **SSH Keys**: Use key-based authentication, not passwords
2. **Limited Access**: Create a dedicated user with minimal permissions if possible
3. **Firewall**: Ensure SSH port (22 or custom) is accessible from billing server
4. **Logs**: Reports may contain domain names but not user data
5. **Retention**: Clean up old reports to save disk space

## Next Steps

After completing this setup:

1. ✅ Verify reports are being generated weekly
2. ✅ Test SSH access from billing server
3. ✅ Run the billing application (see 3_SETUP_GUIDE.md)
4. ✅ Configure domain and CoS mappings
5. ✅ Generate your first billing report

## Summary Checklist

- [ ] Copied script to `/opt/zimbra/MonthlyBillingByDomain-v6.sh`
- [ ] Set script permissions (755) and ownership (zimbra:zimbra)
- [ ] Created `/opt/MonthlyUsageReports/` directory
- [ ] Set directory permissions (744) and ownership (zimbra:zimbra)
- [ ] Added cron jobs to zimbra's crontab
- [ ] Tested script manually
- [ ] Verified report format is correct
- [ ] Set up SSH key authentication
- [ ] Tested SSH access from billing server
- [ ] Added optional report cleanup cron job

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Zimbra logs: `/opt/zimbra/log/`
3. Check cron execution in system logs
4. Verify Zimbra services are running: `zmcontrol status`
5. Test SSH connectivity manually

---

**Ready for billing?** After setting up the Zimbra server, proceed to 3_SETUP_GUIDE.md to configure the billing application.
