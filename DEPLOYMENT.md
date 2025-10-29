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

### Step 3: Add Your API Key (IMPORTANT!)

Before deploying, you need to securely add your Planet API key:

1. In the deployment page, look for **"Secrets"** section
2. Click **"Advanced settings"** → **"Secrets"**
3. Add your secret in TOML format:

```toml
PLANET_API_KEY = "your_actual_planet_api_key_here"
```

4. **Replace** `your_actual_planet_api_key_here` with your real API key

⚠️ **IMPORTANT:** This is secure - secrets are encrypted and never shown in logs!

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

### Step 5: Test Your App

1. Once deployed, test all features:
   - ✅ Search for imagery
   - ✅ Preview images
   - ✅ Upload tide data
   - ✅ Mark exposure status
   - ✅ Export CSV

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

### ✅ DO:
- Store API keys in Streamlit Secrets
- Use environment variables
- Keep secrets.toml in .gitignore

### ❌ DON'T:
- Hardcode API keys in code
- Commit secrets.toml to GitHub
- Share your API key publicly

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError"
**Solution:** Make sure all dependencies are in `requirements.txt`

### Problem: "PLANET_API_KEY not found"
**Solution:** Add the secret in Streamlit Cloud dashboard:
1. Go to app settings
2. Click "Secrets"
3. Add: `PLANET_API_KEY = "your_key"`
4. Save and restart app

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

