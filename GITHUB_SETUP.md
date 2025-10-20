# GitHub Setup Instructions

Follow these steps to publish your project to GitHub.

## Prerequisites

✅ You have a GitHub account
✅ Git is installed on your Mac (it should be by default)

## Step 1: Create Repository on GitHub

1. Go to https://github.com
2. Click the **"+"** icon (top-right) → **"New repository"**
3. Configure:
   - **Repository name**: `zimbra-qbo-billing`
   - **Description**: `Automated billing system for Zimbra email usage to QuickBooks Online`
   - **Visibility**: ✅ **Public** (recommended for open source)
   - **DO NOT** check any initialization options (no README, no .gitignore, no license)
4. Click **"Create repository"**
5. **Copy the repository URL** from the page (looks like: `https://github.com/YOUR-USERNAME/zimbra-qbo-billing.git`)

## Step 2: Configure Git (First Time Only)

If you haven't used Git before, configure your identity:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Use the email associated with your GitHub account.

## Step 3: Initialize Local Repository

```bash
cd /Users/mstone/claude-dir/invoicing

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Zimbra-QBO billing automation v1.0.0

- Complete billing automation system
- QuickBooks Online integration
- Zimbra report parsing
- Interactive reconciliation
- Excel report generation
- MIT licensed for Zimbra partners"
```

## Step 4: Connect to GitHub

Replace `YOUR-USERNAME` with your actual GitHub username:

```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR-USERNAME/zimbra-qbo-billing.git

# Verify remote was added
git remote -v
```

## Step 5: Push to GitHub

```bash
# Push to GitHub (main branch)
git push -u origin main
```

**If you get an error about 'main' not existing**, try:
```bash
# Rename branch to main (if it's called master)
git branch -M main

# Push again
git push -u origin main
```

## Step 6: Verify on GitHub

1. Go to your repository: `https://github.com/YOUR-USERNAME/zimbra-qbo-billing`
2. You should see:
   - All your files listed
   - README.md displayed on the main page
   - MIT License badge
   - Your commit message

## Step 7: Update setup.py with Actual URL

After creating the repository, update the URL in setup.py:

```bash
nano setup.py
```

Change:
```python
url='https://github.com/YOUR-USERNAME/zimbra-qbo-billing',
```

Then commit and push the change:
```bash
git add setup.py
git commit -m "Update repository URL in setup.py"
git push
```

## Optional: Add GitHub Topics

On your GitHub repository page:
1. Click the gear icon next to "About"
2. Add topics (tags): `zimbra`, `quickbooks`, `billing`, `automation`, `python`
3. Save

## Optional: Add README Badge

Add a license badge to your README.md. At the top of 2_README.md, add:

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

## Common Issues

### Authentication Required

If GitHub asks for authentication when pushing:

**Option 1: Use Personal Access Token (Recommended)**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: "Zimbra-QBO Billing"
4. Select scopes: ✅ **repo** (full control)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)
7. When Git asks for password, paste the token (not your GitHub password)

**Option 2: Use SSH** (More secure, but requires setup)
1. Generate SSH key: `ssh-keygen -t ed25519 -C "your.email@example.com"`
2. Add to SSH agent: `ssh-add ~/.ssh/id_ed25519`
3. Copy public key: `cat ~/.ssh/id_ed25519.pub`
4. Go to GitHub → Settings → SSH and GPG keys → New SSH key
5. Paste the public key
6. Change remote URL to SSH:
   ```bash
   git remote set-url origin git@github.com:YOUR-USERNAME/zimbra-qbo-billing.git
   git push
   ```

### Branch Name Issues

If your default branch is `master` instead of `main`:

```bash
# Rename to main
git branch -M main
git push -u origin main
```

### Already Exists Error

If you accidentally initialized the repository on GitHub with a README:

```bash
# Pull first, then push
git pull origin main --allow-unrelated-histories
git push -u origin main
```

## Future Updates

When you make changes:

```bash
# See what changed
git status

# Add changed files
git add .

# Or add specific files
git add src/some_file.py

# Commit with message
git commit -m "Description of changes"

# Push to GitHub
git push
```

## Branching (Advanced)

For major changes, create a branch:

```bash
# Create and switch to new branch
git checkout -b feature-name

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push branch to GitHub
git push -u origin feature-name

# Create Pull Request on GitHub
# After merging, switch back to main
git checkout main
git pull
```

## Important Notes

1. **Never commit sensitive data**:
   - `.env` file is in `.gitignore` (won't be pushed)
   - Database files are excluded
   - Token files are excluded
   - Excel reports are excluded

2. **What IS included**:
   - All source code
   - Documentation
   - LICENSE file
   - `.env.example` (template only)
   - setup.py
   - requirements.txt

3. **Check before pushing**:
   ```bash
   # See what will be committed
   git status

   # See actual file changes
   git diff
   ```

4. **Your credentials are safe**:
   - Real `.env` file is not pushed
   - `.env.example` has placeholder values only
   - Database with customer data is not pushed

## Repository Structure on GitHub

After pushing, your repository will show:

```
zimbra-qbo-billing/
├── 2_README.md (displayed on GitHub homepage)
├── 3_SETUP_GUIDE.md
├── 4_QUICKSTART.md
├── 5_USAGE.md
├── 6_PRODUCTION.md
├── 7_PROJECT_SUMMARY.md
├── LICENSE (MIT)
├── .gitignore
├── .env.example
├── requirements.txt
├── setup.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── database/
│   ├── qbo/
│   ├── reconciliation/
│   ├── reporting/
│   ├── ui/
│   └── zimbra/
└── tests/
```

## Sharing with Others

Once published, share the URL with other Zimbra partners:

```
https://github.com/YOUR-USERNAME/zimbra-qbo-billing
```

They can install it with:
```bash
git clone https://github.com/YOUR-USERNAME/zimbra-qbo-billing.git
cd zimbra-qbo-billing
pip3 install -e .
```

## Next Steps

1. ✅ Push to GitHub (follow steps above)
2. Consider writing a blog post about it
3. Share on Zimbra forums/communities
4. List on awesome-zimbra lists (if they exist)
5. Tweet about it (mention @Zimbra)

---

**Ready?** Start with Step 1 above!
