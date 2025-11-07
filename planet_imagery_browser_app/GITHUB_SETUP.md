# GitHub Setup Instructions

## Your Repository Information

- **Local commits ready**: 2 commits
- **Branch**: master
- **Files included**: 
  - planet_imagery_browser.py (main application)
  - README.md (documentation)
  - requirements.txt (dependencies)
  - LICENSE (MIT)
  - .gitignore (ignore rules)

## After Creating Your GitHub Repository

Run these commands in order:

### 1. Add GitHub as remote origin
Replace `YOUR_USERNAME` with your GitHub username and `REPO_NAME` with your chosen repository name:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

### 2. Rename branch from master to main (GitHub's default)
```powershell
git branch -M main
```

### 3. Push to GitHub
```powershell
git push -u origin main
```

### If you get authentication errors:
- Use a Personal Access Token instead of password
- Go to: https://github.com/settings/tokens
- Generate new token (classic)
- Use token as password when prompted

## Verification

After pushing, visit your repository at:
`https://github.com/YOUR_USERNAME/REPO_NAME`

You should see all your files!

