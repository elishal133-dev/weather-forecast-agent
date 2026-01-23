# Deploy Weather Forecast App - FREE & PUBLIC

Your app is ready to deploy! Follow these steps to make it available to anyone, anywhere, for free with HTTPS.

## Option 1: Render.com (RECOMMENDED - Easiest & Best Free Tier)

### Step 1: Push to GitHub

1. **Create a GitHub account** (if you don't have one): https://github.com/signup

2. **Create a new repository:**
   - Go to https://github.com/new
   - Name it: `weather-forecast-agent`
   - Make it **Public**
   - Don't initialize with README
   - Click "Create repository"

3. **Push your code to GitHub:**
   Open Command Prompt in the project folder and run:
   ```cmd
   cd C:\Users\User\weather-forecast-agent
   git init
   git add .
   git commit -m "Initial commit - Weather Forecast Aggregator"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/weather-forecast-agent.git
   git push -u origin main
   ```

### Step 2: Deploy to Render

1. **Sign up for Render.com:**
   - Go to https://render.com
   - Click "Get Started for Free"
   - Sign up with your GitHub account

2. **Create a new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `weather-forecast-agent`
   - Click "Connect"

3. **Configure the service:**
   - **Name:** `weather-forecast-app` (or your preferred name)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** `Free`
   - Click "Create Web Service"

4. **Wait for deployment (5-10 minutes)**
   - Render will build and deploy your app
   - You'll get a URL like: `https://weather-forecast-app.onrender.com`

5. **Done!** Your app is now live with HTTPS!

### Free Tier Limits:
- ✅ 750 hours/month (enough for 24/7)
- ✅ Automatic HTTPS
- ✅ Custom domain support
- ⚠️ App sleeps after 15 min of inactivity (free tier)
- ⚠️ Takes ~30 seconds to wake up on first request

---

## Option 2: PythonAnywhere (Good Alternative)

### Steps:

1. **Sign up:**
   - Go to https://www.pythonanywhere.com/registration/register/beginner/
   - Create a free account

2. **Upload your code:**
   - Go to "Files" tab
   - Upload your project files

3. **Create a web app:**
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Flask"
   - Point to your `app.py` file

4. **Install dependencies:**
   - Open a Bash console
   - Run: `pip3 install --user -r requirements.txt`

5. **Reload the web app**
   - Your app will be live at: `https://yourusername.pythonanywhere.com`

### Free Tier Limits:
- ✅ Always on (no sleeping)
- ✅ Automatic HTTPS
- ⚠️ 512 MB storage
- ⚠️ Custom domain requires paid plan

---

## Option 3: Railway.app (Modern & Fast)

1. **Sign up:** https://railway.app
2. **New Project** → "Deploy from GitHub repo"
3. Connect your repository
4. Railway auto-detects Flask and deploys
5. Get URL: `https://your-app.railway.app`

**Free tier:** $5 credit/month (usually enough for small apps)

---

## After Deployment

### Share Your App:
Once deployed, share the HTTPS URL with anyone:
- Friends/family can access from any device
- Works on any phone (Android, iOS)
- No installation needed
- Secure HTTPS connection

### Monitor Your App:
- Check logs in your hosting dashboard
- Monitor uptime and performance
- Update by pushing to GitHub (auto-deploys)

### Future Enhancements:
- Add custom domain name
- Set up monitoring alerts
- Add more weather sources
- Implement user preferences/favorites

---

## Troubleshooting

**App won't start:**
- Check logs in hosting dashboard
- Verify all dependencies in requirements.txt
- Ensure port configuration is correct

**App is slow:**
- Free tiers may have limited resources
- Consider upgrading to paid tier if needed
- Optimize API calls and caching

**Need help?**
- Render docs: https://render.com/docs
- PythonAnywhere forum: https://www.pythonanywhere.com/forums/
- Railway docs: https://docs.railway.app/
