# Project Overview

```
######################################
# Goals:                             #
######################################
```

The software in this repo will help you as Zimbra BSP, if you use QuickBooks Online ("QBO"), to automate monthly invoicing "The Mission Critical Email Way".

```
######################################
# Our Way:                           #
######################################
```

We use Classes of Service to set pricing; bigger quotas, more features, etc. Each Class of Service in Zimbra can be (and is) mapped to a List Item in QBO.

Once you've done that, you are almost ready to use our software, which we are Open Sourcing via an MIT license.

```
######################################
# Get The Usage Data By CoS:         #
######################################
```

Next, you need to run a script on one of your Zimbra mailbox servers that will, weekly, via a cron job, generate plain-text usage reports. The script, which took us a few months to develop, is included.

```
######################################
# Process The Data Monthly           #
# Generate Invoices Automatically    #
# Approve and Send Invoices Manually #
######################################
```

We then crafted some Python code that:
1. Downloads the Usage Data reports from the Zimbra mailbox server.
2. Talks to QBO to make sure that email domains are mapped to QBO Customers.
3. Talks to QBO to make sure that Classes of Service are mapped to QBO List Items.
4. Prompts the user to map any unmapped email domains and/or Classes of Service.
5. Creates Draft invoices in QBO.
6. Generates an Excel spreadsheet for tracking purposes.

All you need to do is review and email out the invoices from QBO! (Well, and watch your receivables to be sure you get paid...)

The code is licensed under the MIT License for Open Source projects.

If you find any issues or have any suggestions for improvement, please send those along.

Be kind; pay it forward.

---

Hope that helps,

**L. Mark Stone**
Mark.Stone@MissionCriticalEmail.com
Mission Critical Email, LLC
20 October, 2025
