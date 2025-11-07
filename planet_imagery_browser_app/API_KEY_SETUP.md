# Quick API Key Setup Guide 🔑

This guide will help you set up your Planet API key in just a few minutes.

## 🚀 Quick Start (Windows)

### Option 1: Use the Automated Script (Easiest!)

1. **Right-click on PowerShell** and select **"Run as Administrator"**

2. **Navigate to the project folder**:
```powershell
cd "E:\OneDrive - James Cook University\Seagrass Monitoring_DropBox folder\MMP\Tidal data\Exposure_pred_from_ITEM_and_eotides\planet_imagery_browser_app"
```

3. **Run the setup script**:
```powershell
.\setup_api_key.ps1
```

4. **Follow the prompts** to enter your API key

5. **Close and reopen** your terminal

Done! ✅

---

### Option 2: Manual Setup (2 Minutes)

1. **Get your API key** from https://www.planet.com/account/

2. **Open PowerShell as Administrator**:
   - Right-click Start → "Windows PowerShell (Admin)" or "Terminal (Admin)"

3. **Run this command** (replace `YOUR_KEY` with your actual key):
```powershell
[System.Environment]::SetEnvironmentVariable('PLANET_API_KEY', 'PLAKxxxxxxxxxxxxxxxxxxxxx', 'User')
```

4. **Close and reopen** your terminal

5. **Verify it worked**:
```powershell
$env:PLANET_API_KEY
```
You should see your API key displayed.

---

## ✅ Testing Your Setup

After setting up your API key, test it:

```powershell
# 1. Activate your conda environment
conda activate planet

# 2. Check if the key is set
$env:PLANET_API_KEY

# 3. Run the application
python planet_imagery_browser.py
```

If the application opens without asking for an API key, you're all set! 🎉

---

## 🔍 Troubleshooting

### Problem: Script won't run - "execution policy" error

**Error message:**
```
.\setup_api_key.ps1 : File cannot be loaded because running scripts is disabled on this system.
```

**Solution:**
Run this command first (as Administrator):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try running the script again.

---

### Problem: API key not found after restart

**Solution:**
Make sure you ran PowerShell **as Administrator** when setting the key.

---

### Problem: "Access denied" when setting environment variable

**Solution:**
Right-click PowerShell and select "Run as Administrator"

---

## 🔐 Security Notes

- ✅ Your API key is stored in Windows User environment variables (secure)
- ✅ The key is only accessible to your Windows user account
- ✅ The key persists across reboots
- ❌ Never share your API key with others
- ❌ Never commit your API key to GitHub

---

## 📚 Alternative: Set Key Per Session

If you don't want to set the key permanently, you can set it for each session:

```powershell
# Run this every time you open PowerShell
$env:PLANET_API_KEY="PLAKxxxxxxxxxxxxxxxxxxxxx"
```

Or just let the application prompt you for the key each time you run it (easiest but not persistent).

---

## 🆘 Still Having Issues?

Check the full README.md for more detailed instructions, or:

1. Verify your Planet account is active at https://www.planet.com/
2. Make sure your API key starts with "PLAK"
3. Try the dialog prompt method (just run the app without setting the key)

---

**Need your API key?** 
→ https://www.planet.com/account/#/user-settings/api-keys

