# 🚀 Deploying Planet Imagery Browser to Streamlit Cloud

This guide will help you deploy the web version of Planet Imagery Browser for **FREE** on Streamlit Cloud!

## 📋 Prerequisites

- ✅ GitHub account
- ✅ Planet API key
- ✅ Your code already pushed to GitHub (you have this!)

## 🌐 What is Streamlit Cloud?

Streamlit Cloud is a **FREE** hosting platform for Streamlit apps that:
- 🆓 Provides **unlimited public apps** for free
- 🔄 **Auto-deploys** from GitHub when you push changes
- 🌍 Gives you a **public URL** to share
- 🔒 Secure secrets management for API keys

## 🎯 Step-by-Step Deployment

### Step 1: Sign Up for Streamlit Cloud

1. Go to: **https://streamlit.io/cloud**
2. Click **"Sign up"**
3. **Sign in with GitHub** (recommended - easiest integration)
4. Authorize Streamlit to access your GitHub repositories

### Step 2: Create New App

1. Once logged in, click **"New app"**
2. You'll see three fields to fill:

   **Repository:**
   ```
   lucas-langlois/planet-imagery-browser
   ```

   **Branch:**
   ```
   main
   ```

   **Main file path:**
   ```
   planet_imagery_browser_streamlit.py
   ```

3. Click **"Advanced settings"** (optional but recommended)
   - **Python version:** 3.9 (or 3.10)
   - Leave other settings as default

### Step 3: Configure Deployment Settings (Optional)

**Good News!** 🎉 The app is designed so users enter their own API keys directly in the interface.

You can deploy immediately without any secrets configuration!

**Optional: Set a Default API Key** (Advanced)

If you want to provide a default API key for testing or internal use:

1. In the deployment page, look for **"Secrets"** section
2. Click **"Advanced settings"** → **"Secrets"**
3. Add your secret in TOML format:

```toml
PLANET_API_KEY = "your_actual_planet_api_key_here"
```

⚠️ **Note:** Even if you set a default key, users can still enter their own keys in the app interface.

### Step 4: Deploy! 🚀

1. Click **"Deploy!"**
2. Wait 2-3 minutes while Streamlit:
   - ✅ Clones your repository
   - ✅ Installs dependencies from `requirements.txt`
   - ✅ Starts your app
3. Your app will be live at:
   ```
   https://lucas-langlois-planet-imagery-browser.streamlit.app
   ```
   (or similar URL)

### Step 5: Enter Your API Key & Test

1. Once deployed, the app will prompt you to enter your Planet API key
2. Enter your API key (starts with `PLAK...`)
3. Click **"Connect"**
4. Test all features:
   - ✅ Search for imagery
   - ✅ Preview images
   - ✅ Upload tide data
   - ✅ Mark exposure status
   - ✅ Export CSV

**Sharing with Others:** 

Each user enters their own API key when they first use the app. Keys are stored securely in their browser session (not on the server) and are never saved permanently.

## 🔄 Updating Your App

The beauty of Streamlit Cloud: **automatic deployments!**

Whenever you push changes to GitHub:
```bash
git add .
git commit -m "Update features"
git push
```

Streamlit Cloud will **automatically** redeploy your app in 1-2 minutes! 🎉

## 📊 Managing Your App

### App Dashboard

Access at: **https://share.streamlit.io/**

From the dashboard you can:
- 📈 View app analytics
- 🔄 Restart the app
- 🔧 Edit secrets
- ⚙️ Change settings
- 🗑️ Delete the app

### App Settings

Click on your app → ⚙️ **Settings** to:
- Change Python version
- Update secrets (API keys)
- View logs
- Configure custom domain (paid feature)

### View Logs

If something goes wrong:
1. Click on your app in the dashboard
2. Click **"Manage app"** → **"Logs"**
3. See real-time logs for debugging

## 🆓 Free Tier Limits

Streamlit Cloud FREE tier includes:

| Feature | Free Tier |
|---------|-----------|
| Public apps | **Unlimited** ✅ |
| Private apps | 1 app |
| Resources | 1 GB RAM, shared CPU |
| Secrets | Unlimited |
| Auto-deploy | ✅ Yes |
| Custom domain | ❌ No (paid only) |

**For our app:** The free tier is perfect! ✅

## 🔒 Security Best Practices

### How API Keys Are Handled

**✅ Secure by Design:**
- Users enter their own API keys in the app interface
- Keys are stored in **browser session state only** (not on the server)
- Keys are never saved to disk or database
- Keys are automatically cleared when the browser session ends
- Each user's key is isolated from other users

**Privacy Benefits:**
- ✅ You (the deployer) never see users' API keys
- ✅ Users maintain control of their own keys
- ✅ No central key storage = no data breach risk
- ✅ Works great for sharing with students/colleagues

### ✅ DO:
- Keep your API key private
- Never share screenshots with your API key visible
- Log out when using shared computers
- Keep secrets.toml in .gitignore (if using local secrets)

### ❌ DON'T:
- Share your API key publicly
- Hardcode API keys in source code
- Commit API keys to GitHub
- Share your Planet account credentials

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError"
**Solution:** Make sure all dependencies are in `requirements.txt`

### Problem: "PLANET_API_KEY not found" or "Invalid API Key"
**Solution:** The app now prompts users to enter their API key directly in the interface. Each user should:
1. Get their API key from https://www.planet.com/account
2. Enter it in the app when prompted
3. Click "Connect"

If you want to provide a default key for everyone, add it in Streamlit Cloud settings (optional).

### Problem: App is slow or crashes
**Solution:** Free tier has resource limits
- Reduce image preview sizes
- Cache expensive operations
- Consider upgrading to paid tier if needed

### Problem: Changes not showing up
**Solution:** 
1. Make sure changes are pushed to GitHub
2. Wait 1-2 minutes for auto-deploy
3. Hard refresh browser (Ctrl+F5)
4. Or manually reboot app in dashboard

## 🌟 Making Your App Public

Once deployed, share your app by:

1. **Copy the URL** from Streamlit Cloud dashboard
2. **Share it** with colleagues/students:
   ```
   https://your-username-planet-imagery-browser.streamlit.app
   ```

3. **Optional:** Add the URL to your GitHub README:
   ```markdown
   ## 🌐 Live Demo
   Try it here: [Planet Imagery Browser](https://your-url.streamlit.app)
   ```

## 📈 Next Steps

### After Deployment:

1. ✅ Test all features
2. ✅ Share URL with team
3. ✅ Add feedback mechanism
4. ✅ Monitor usage in dashboard

### Optional Enhancements:

- 🔐 Add authentication (streamlit-authenticator)
- 💾 Add database for persistent storage
- 📧 Add email notifications
- 🎨 Customize theme colors
- 📱 Optimize for mobile

## 💰 Cost Summary

| Item | Cost |
|------|------|
| Streamlit Cloud (Free tier) | **$0/month** ✅ |
| GitHub (public repo) | **$0/month** ✅ |
| Domain name (optional) | ~$10-15/year |
| **TOTAL for basic setup** | **$0/month** 🎉 |

## 🆘 Need Help?

- **Streamlit Docs:** https://docs.streamlit.io/streamlit-community-cloud
- **Streamlit Forum:** https://discuss.streamlit.io/
- **GitHub Issues:** Open an issue in your repo

## 🎓 Learning Resources

- [Streamlit Gallery](https://streamlit.io/gallery) - Example apps
- [Streamlit Cheat Sheet](https://docs.streamlit.io/library/cheatsheet)
- [Streamlit Tutorial](https://docs.streamlit.io/library/get-started)

---

**You're all set! Happy deploying! 🚀**

Questions? Check the [main README](README.md) or open an issue on GitHub.

