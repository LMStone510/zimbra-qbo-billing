# GitHub Publishing Checklist

Quick checklist for publishing your project to GitHub.

## ☐ Part 1: Create Repository on GitHub (5 minutes)

1. ☐ Go to https://github.com
2. ☐ Click **"+"** (top-right) → **"New repository"**
3. ☐ Enter name: `zimbra-qbo-billing`
4. ☐ Enter description: `Automated billing system for Zimbra email usage to QuickBooks Online`
5. ☐ Select: **Public**
6. ☐ **DO NOT** check any boxes (no README, no .gitignore, no license)
7. ☐ Click **"Create repository"**
8. ☐ Copy the repository URL (something like: `https://github.com/YOUR-USERNAME/zimbra-qbo-billing.git`)

**Write URL here**: _________________________________

## ☐ Part 2: Configure Git (First Time Only) (2 minutes)

Only if you haven't used Git before:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

- ☐ Run the two commands above with your info

## ☐ Part 3: Push Your Code (5 minutes)

Run these commands in Terminal:

```bash
cd ~/zimbra-qbo-billing
```

**Initialize and commit**:
```bash
git init
git add .
git commit -m "Initial commit: Zimbra-QBO billing automation v1.12.1"
```

- ☐ Ran `git init`
- ☐ Ran `git add .`
- ☐ Ran `git commit`

**Connect to GitHub** (replace YOUR-USERNAME with your actual username):
```bash
git remote add origin https://github.com/YOUR-USERNAME/zimbra-qbo-billing.git
```

- ☐ Ran `git remote add origin` command

**Push to GitHub**:
```bash
git branch -M main
git push -u origin main
```

- ☐ Ran `git branch -M main`
- ☐ Ran `git push -u origin main`

## ☐ Part 4: Verify (2 minutes)

1. ☐ Go to your repository on GitHub
2. ☐ See all files listed
3. ☐ See README displayed on main page
4. ☐ Click "LICENSE" file - see MIT License
5. ☐ Click through a few files - see copyright headers

## ☐ Part 5: Update setup.py (2 minutes)

```bash
nano setup.py
```

- ☐ Change the URL line to your actual GitHub URL
- ☐ Save (Ctrl+O, Enter, Ctrl+X)

```bash
git add setup.py
git commit -m "Update repository URL"
git push
```

- ☐ Committed and pushed the change

## ☐ Optional Enhancements

- ☐ Add topics on GitHub: `zimbra`, `quickbooks`, `billing`, `automation`, `python`
- ☐ Add license badge to README
- ☐ Share URL with Zimbra community
- ☐ Add to your website/profile

## Troubleshooting

**If GitHub asks for password:**
- Don't use your GitHub password
- Use a Personal Access Token instead
- See GITHUB_SETUP.md for detailed instructions

**If you get "branch main doesn't exist":**
```bash
git branch -M main
git push -u origin main
```

**If you get "already exists" error:**
You might have initialized the repo with files on GitHub. See GITHUB_SETUP.md.

## Done! ✓

Your project is now open source and available to other Zimbra partners at:

`https://github.com/YOUR-USERNAME/zimbra-qbo-billing`

Share this URL with others who want to use it!

---

**Need more help?** See GITHUB_SETUP.md for detailed instructions and troubleshooting.
