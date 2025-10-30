# Step 1: QuickBooks Developer Setup

**Version**: v1.13.0

**Goal**: Register for a QuickBooks Developer account, create a Development application, and set up a Sandbox company for testing.

**Time Required**: 30-45 minutes

**Prerequisites**:
- Active Intuit account (create one at https://accounts.intuit.com if needed)
- Access to QuickBooks Online (production account recommended but not required for testing)

---

## Overview

Before you can use the billing automation application, you need to register as an Intuit developer and create an application that will connect to QuickBooks Online. This step is essential for both testing (sandbox) and production use.

**What you'll accomplish:**
1. Register for an Intuit Developer account
2. Create a new application in the Intuit Developer portal
3. Obtain your OAuth2 credentials (Client ID and Client Secret)
4. Create a QuickBooks Sandbox company for testing
5. Configure your application's redirect URI
6. Understand the difference between Sandbox and Production environments

---

## Step 1.1: Register for Intuit Developer Account

1. **Go to the Intuit Developer Portal**
   - Navigate to: https://developer.intuit.com
   - Click **"Sign In"** (top right)

2. **Sign in with your Intuit Account**
   - Use your existing Intuit/QuickBooks credentials
   - Or create a new account if you don't have one

3. **Accept Developer Terms**
   - Review and accept the Intuit Developer Agreement
   - Complete any required profile information

---

## Step 1.2: Create Your Application

1. **Access the Dashboard**
   - After signing in, click **"My Apps"** in the navigation
   - Or go directly to: https://developer.intuit.com/app/developer/myapps

2. **Create a New App**
   - Click **"Create an app"** button
   - Select **"QuickBooks Online and Payments"**

3. **Name Your Application**
   - **App Name**: `Zimbra Billing Automation` (or your company name)
   - **Description**: `Automated monthly billing for Zimbra email services`
   - Click **"Create app"**

4. **Configure App Settings**
   - You'll be taken to your app's dashboard
   - Click on **"Keys & credentials"** in the left menu

---

## Step 1.3: Get Your OAuth2 Credentials

On the **Keys & credentials** page, you'll see two sections: **Development** and **Production**.

### Development Keys (For Sandbox Testing)

1. **Client ID (Development)**
   - Copy this value - you'll need it for `.env` configuration
   - Format: Long alphanumeric string (e.g., `ABcd1234EFgh5678IJkl9012MNop3456QRst7890`)

2. **Client Secret (Development)**
   - Click **"Show"** to reveal the secret
   - Copy this value - you'll need it for `.env` configuration
   - **Important**: Keep this secret secure! Never commit it to version control

3. **Redirect URIs**
   - Click **"Add URI"**
   - Enter: `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl`
   - Click **"Save"**
   - This is Intuit's OAuth2 Playground redirect URL that works reliably for desktop applications

---

## Step 1.4: Create a Sandbox Company

Sandbox companies are test environments provided by Intuit for development.

1. **Navigate to Sandbox**
   - In the developer portal, click **"Sandbox"** in the left menu
   - Or go to: https://developer.intuit.com/app/developer/sandbox

2. **Create a New Sandbox Company**
   - Click **"Create sandbox company"** or **"Add Company"**
   - Select **"QuickBooks Online"**
   - Choose a company type: **"United States"** (or your region)

3. **Wait for Creation**
   - Sandbox creation takes 1-2 minutes
   - You'll see a loading indicator

4. **Note Your Sandbox Company ID**
   - Once created, you'll see your sandbox company listed
   - **Company ID (Realm ID)**: This is the long number next to your company name
   - Copy this - you'll need it for `.env` configuration
   - Format: 10-16 digit number (e.g., `1234567890123456`)

5. **Access Your Sandbox Company**
   - Click **"Sign in to Company"** to explore your test company
   - This opens QuickBooks Online in sandbox mode
   - Pre-populated with sample data (customers, items, invoices)

---

## Step 1.5: Set Up Sandbox Company

Your sandbox company needs some initial setup for billing automation.

### Add Service Items (For CoS Mapping)

The billing system maps each Zimbra Class of Service (CoS) to a QuickBooks "Product/Service" item.

1. **Sign in to your Sandbox Company**
   - From the developer portal sandbox page, click **"Sign in to Company"**

2. **Navigate to Products and Services**
   - Click the gear icon (⚙️) in the top right
   - Select **"Products and Services"** under **Lists**
   - Or go to: Sales → Products and Services

3. **Create Service Items for Your CoS Types**

   For each Zimbra Class of Service you bill for, create a corresponding service item:

   **Example CoS → QBO Item Mappings:**
   - `customer-2gb` → "Email Hosting - 2GB Mailbox"
   - `customer-10gb` → "Email Hosting - 10GB Mailbox"
   - `customer-25gb` → "Email Hosting - 25GB Mailbox"
   - `customer-50gb` → "Email Hosting - 50GB Mailbox"

   **To create each item:**
   - Click **"New"** → **"Service"**
   - **Name**: Descriptive name (e.g., "Email Hosting - 2GB Mailbox")
   - **SKU**: Optional (e.g., "EMAIL-2GB")
   - **Category**: Create or select "Email Services"
   - **Description**: What the customer sees on invoices
   - **Sales price/rate**: Your monthly rate per mailbox (e.g., $5.00)
   - **Income account**: Select appropriate revenue account
   - Click **"Save and close"**

4. **Verify Your Items**
   - You should now see all your service items listed
   - These will be available when you run the billing system

### Add Test Customers (Optional)

You can add a few test customers that match your actual domain names:

1. **Navigate to Customers**
   - Click **"Sales"** → **"Customers"**
   - Or click the **"New"** button → **"Customer"**

2. **Create Test Customers**
   - **Display name**: Customer or company name
   - **Email**: Test email address
   - Add any other relevant details
   - Click **"Save"**

3. **Create 3-5 test customers** to represent real customers you'll bill

---

## Step 1.6: Understand Sandbox vs Production

### Sandbox Environment

**Purpose**: Development and testing
- ✅ Free to use
- ✅ Pre-populated with sample data
- ✅ Safe to experiment without affecting real data
- ✅ API calls don't count against production limits
- ❌ Data is isolated from your real QuickBooks
- ❌ Cannot send real invoices to customers
- ❌ Resets periodically (save your test data elsewhere)

**When to use Sandbox:**
- Initial application setup and configuration
- Testing the billing workflow
- Mapping domains and CoS
- Generating test invoices and reports
- Training team members
- Troubleshooting issues

### Production Environment

**Purpose**: Real business operations
- ✅ Connected to your real QuickBooks Online company
- ✅ Creates real invoices for real customers
- ✅ Data persists permanently
- ✅ Invoices can be sent to customers
- ⚠️ Changes affect your actual books
- ⚠️ API calls count against rate limits
- ⚠️ Requires separate production OAuth credentials

**When to use Production:**
- After successful sandbox testing
- Ready to bill real customers
- Monthly billing operations
- Real invoice generation

---

## Step 1.7: Save Your Credentials

You now have all the credentials needed for sandbox testing. Save these securely:

**From Intuit Developer Portal:**
- ✅ **Development Client ID**: `ABcd1234EFgh5678IJkl9012MNop3456QRst7890`
- ✅ **Development Client Secret**: `xyz789abc123def456ghi789`
- ✅ **Redirect URI**: `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl`
- ✅ **Sandbox Company ID (Realm ID)**: `1234567890123456`

**You'll use these in Step 3** when deploying the billing application.

---

## Step 1.8: Production Keys (For Later)

You don't need production keys yet, but here's how to get them when you're ready:

### Applying for Production Keys

1. **Complete Your App Profile**
   - In the developer portal, complete all required app information
   - Add app description, privacy policy URL, and terms of service
   - Specify scopes needed: `com.intuit.quickbooks.accounting`

2. **Submit for Production**
   - Click **"Go to Production"** or **"Production"** tab
   - Review Intuit's production requirements
   - Submit your app for review (usually approved quickly)

3. **Production Credentials**
   - Once approved, you'll see **Production** keys on the "Keys & credentials" page
   - **Production Client ID** and **Client Secret** are different from Development
   - You'll switch to these in **Step 4: Production Deployment**

---

## Troubleshooting

### Can't Create Sandbox Company

**Problem**: "Create sandbox company" button is grayed out
- **Solution**: Ensure you've created an app first (Step 1.2)
- **Solution**: Try refreshing the page or signing out/in

### Lost My Client Secret

**Problem**: I didn't copy my client secret
- **Solution**: Click "Show" again on the Keys & credentials page
- **Solution**: If you can't see it, you may need to regenerate it (will invalidate old secret)

### Redirect URI Not Working

**Problem**: OAuth callback fails with "redirect_uri mismatch"
- **Solution**: Ensure `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl` is added to your app
- **Solution**: Verify it's saved (must click "Save" button)
- **Solution**: Match exactly - include https, no trailing slash
- **Note**: `localhost` URLs don't work reliably - use Intuit's OAuth2 Playground URL

### Can't Find Company ID

**Problem**: Where is my sandbox company ID?
- **Solution**: It's on the Sandbox page in the developer portal
- **Solution**: It's the long number shown next to your company name
- **Solution**: You'll also see it in the URL when you sign in to the sandbox company

### Sandbox Company Expired

**Problem**: My sandbox data disappeared
- **Solution**: Sandbox companies can be reset by Intuit periodically
- **Solution**: You can recreate them anytime for free
- **Solution**: For permanent testing, keep backups of your configuration

---

## Summary Checklist

Before proceeding to Step 2, ensure you have:

- [ ] Registered for an Intuit Developer account
- [ ] Created an application in the developer portal
- [ ] Obtained your Development Client ID
- [ ] Obtained your Development Client Secret
- [ ] Added redirect URI: `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl`
- [ ] Created a QuickBooks Sandbox company
- [ ] Noted your Sandbox Company ID (Realm ID)
- [ ] Added service items to sandbox company for your CoS types
- [ ] (Optional) Added test customers to sandbox
- [ ] Saved all credentials securely

---

## What's Next?

✅ **You've completed Step 1!**

**Next Step**: [2_ZIMBRA_SERVER_SETUP.md](2_ZIMBRA_SERVER_SETUP.md)

In Step 2, you'll install the usage report script on your Zimbra mailbox server to generate weekly billing data.

---

## Additional Resources

- **Intuit Developer Portal**: https://developer.intuit.com
- **QuickBooks API Documentation**: https://developer.intuit.com/app/developer/qbo/docs/get-started
- **OAuth 2.0 Guide**: https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization
- **Sandbox Best Practices**: https://developer.intuit.com/app/developer/qbo/docs/develop/sandboxes
