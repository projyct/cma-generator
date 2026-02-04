# CMA Generator - Deployment Guide

## 🚀 Currently Deployed

**Deployment Details:**
- **Platform:** Streamlit Community Cloud (Free Tier)
- **Repository:** https://github.com/projyct/cma-generator
- **Branch:** main
- **Account:** projyct
- **Status:** ✅ Active (Password Protected)
- **Deployed:** February 3, 2026
- **Last Updated:** Auto-deploys on push to main branch
- **Access:** Contact repository owner for credentials

**Features:**
- Pre-loaded with 4,738 demo properties (PII removed)
- Geocoded addresses ready for immediate CMA generation
- Mobile-optimized UI (responsive design)
- Password authentication (protects RentCast API quota)

---

## Repository Cleaned for Deployment ✅

The repository has been cleaned and is now ready for deployment to Streamlit Cloud or other hosting platforms.

## Files Remaining (Production Ready)

### Core Application Files:
- **app.py** - Main Streamlit application (41KB)
- **database.py** - Dual-engine database (SQLite/PostgreSQL) with auto-detection (27KB)
- **parsers.py** - AppFolio CSV parsing (19KB)
- **geocoder.py** - Address geocoding with Census API (16KB)
- **reports.py** - PDF/Excel/HTML report generation (19KB)
- **address_cleaner.py** - Address standardization (17KB)
- **zillow_scraper.py** - Zillow integration placeholder (5KB)

### Configuration Files:
- **requirements.txt** - Python dependencies
- **.gitignore** - Git ignore rules
- **.streamlit/config.toml** - Streamlit configuration
- **.env.example** - Environment variable template (optional)
- **README.md** - Project documentation

### Data Directories:
- **data/** - Database storage (excluded from git)
- **exports/** - Generated reports (excluded from git)

## Removed Files

The following files were removed as they're not needed for deployment:

- ❌ All executable/build files (launcher.py, *.spec, build scripts)
- ❌ Build documentation (BUILD_INSTRUCTIONS.md, etc.)
- ❌ Test scripts (test_*.py)
- ❌ Migration scripts (migrate_*.py)
- ❌ Analysis scripts (analyze_*.py, check_*.py)
- ❌ Build artifacts (build/, dist/, __pycache__)
- ❌ Temporary files

## Deploying to Streamlit Community Cloud

### Prerequisites:
1. GitHub account
2. Repository pushed to GitHub
3. Streamlit Community Cloud account (free at share.streamlit.io)

### Steps:

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Cleaned repository for deployment"
   git push origin main
   ```

2. **Go to Streamlit Cloud:**
   - Visit: https://share.streamlit.io/
   - Click "New app"
   - Connect your GitHub repository
   - Select branch: `main`
   - Main file path: `app.py`
   - Click "Deploy"

3. **Configure Secrets (Required for Database & RentCast):**
   - Go to App settings > Secrets
   - Add environment variables:
     ```toml
     # Required: Neon PostgreSQL connection for persistent storage
     DATABASE_URL = "postgresql://user:password@host/database?sslmode=require"

     # Recommended: For RentCast market comparables
     RENTCAST_API_KEY = "your_rentcast_api_key_here"
     ```

   - **Setup Neon PostgreSQL (Free Forever):**
     1. Sign up at https://neon.tech
     2. Create a new project (PostgreSQL 17, AWS us-east-1)
     3. Copy connection string from Neon dashboard
     4. Add as DATABASE_URL in Streamlit secrets
     5. Free tier: 512 MB storage, never pauses

   - **Get your free RentCast API key:**
     1. Sign up at https://app.rentcast.io/
     2. Go to https://app.rentcast.io/app/api
     3. Copy your API key
     4. Free tier: 50 requests/month (each returns up to 25 comps)

4. **Wait for deployment** (2-5 minutes)

5. **Your app is live!**
   - URL will be: `https://your-app-name.streamlit.app`

## Environment Variables

### Optional Configuration

```toml
# .streamlit/secrets.toml (on Streamlit Cloud)

# Required: Neon PostgreSQL for persistent storage
DATABASE_URL = "postgresql://user:password@host/database?sslmode=require"

# Recommended: For RentCast external market data
RENTCAST_API_KEY = "your_api_key_here"
```

**Note:**
- **DATABASE_URL required:** Provides persistent storage for RentCast cache and property data
- **Without RentCast key:** Uses only internal rent roll data for comparables
- **With RentCast key:** Adds nationwide market comparables + caches them for reuse

## Database Persistence

### Current Approach: Neon PostgreSQL ✅

**Production database using Neon (free forever):**
- **Engine:** PostgreSQL 17 (serverless)
- **Storage:** 512 MB (free tier)
- **Region:** AWS us-east-1
- **Never pauses:** Always available (unlike Supabase)
- **Connection:** Configured via DATABASE_URL environment variable

**Why Neon PostgreSQL:**
- ✅ **Persistent storage:** RentCast cache survives app restarts
- ✅ **Free forever:** No time limits (vs AWS 12 months)
- ✅ **No pausing:** Instant responses (vs Supabase 1-week pause)
- ✅ **Dual-engine support:** database.py auto-detects and uses PostgreSQL when DATABASE_URL is set, falls back to SQLite for local development

**Migration from SQLite:**
- Database layer supports both SQLite and PostgreSQL
- Automatic SQL syntax conversion (AUTOINCREMENT → SERIAL, julianday → EXTRACT)
- Local development uses SQLite (`data/cma_generator.db`)
- Production (Streamlit Cloud) uses Neon PostgreSQL

**Legacy Approach (Pre-Migration):**
The app previously included a pre-populated SQLite database in the repository with 4,738 demo properties. This approach was limited because Streamlit Cloud's ephemeral storage reset the RentCast cache on every restart, wasting API calls.

## Application Features

### Current Functionality:
✅ Upload AppFolio rent roll CSV
✅ Parse property data with smart address extraction
✅ Geocode addresses using Census Batch API (143x faster)
✅ Generate CMA reports with comparable properties search
✅ **RentCast API integration** - Nationwide market comparables
✅ **Smart caching** - Save API responses for reuse (ToS compliant)
✅ Export to PDF, Excel, and HTML
✅ View and manage properties database
✅ Manual address entry for CMA generation

### Performance:
- **Demo:** Instant CMA generation (pre-loaded data)
- **New rent roll import:** ~3 minutes for 4700 properties (geocoding rate-limited)
- **Re-import:** ~10 seconds (skips already-geocoded properties)
- **CMA generation:** < 1 second
- **Report export:** 2-5 seconds

### Mobile Optimization:
✅ Responsive layout (centered, not wide)
✅ Collapsed sidebar (hamburger menu on mobile)
✅ Touch-friendly buttons (44px minimum)
✅ Mobile-optimized input fields (prevents auto-zoom)
✅ Horizontal scrolling for tables when needed
✅ Optimized column widths

## Resource Requirements

### Streamlit Community Cloud (Free Tier):
- ✅ 1 GB RAM - Sufficient
- ✅ 1 CPU core - Sufficient
- ✅ 1 GB storage - Sufficient
- ✅ Python 3.8+ - Supported

The app runs well within free tier limits.

## Monitoring and Maintenance

### Health Checks:
- Streamlit Cloud provides built-in health monitoring
- App automatically restarts on crashes
- View logs in Streamlit Cloud dashboard

### Updates:
1. Make changes locally
2. Test thoroughly
3. Commit and push to GitHub
4. Streamlit Cloud auto-deploys within minutes

## Security Considerations

### Current Status:
- ✅ No sensitive data in repository
- ✅ Environment variables properly excluded
- ✅ User data not persisted (ephemeral database)
- ✅ No authentication (public access)

### For Production Use:
Consider adding:
- User authentication (Streamlit Auth, OAuth)
- Data encryption
- User-specific databases
- Access logs
- Rate limiting

## Alternative Deployment Options

### 1. Heroku
```bash
# Add Procfile:
web: streamlit run app.py --server.port=$PORT

# Deploy:
git push heroku main
```

### 2. AWS EC2
- Launch t2.micro instance
- Install Python and dependencies
- Run with systemd service

### 3. Docker Container
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

### 4. Google Cloud Run
- Build container image
- Deploy serverless
- Auto-scaling included

## Troubleshooting

### Issue: App won't start
**Check:**
- requirements.txt is complete
- No syntax errors in Python files
- Logs in Streamlit Cloud dashboard

### Issue: Geocoding fails
**Check:**
- Census API is accessible
- Rate limiting not exceeded
- Address format is correct

### Issue: Reports won't generate
**Check:**
- ReportLab fonts available
- Sufficient disk space
- PDF generation dependencies installed

## Next Steps

1. **Test locally** one more time:
   ```bash
   streamlit run app.py
   ```

2. **Commit cleaned repository:**
   ```bash
   git add .
   git commit -m "Repository cleaned for deployment"
   ```

3. **Push to GitHub:**
   ```bash
   git push origin main
   ```

4. **Deploy to Streamlit Cloud:**
   - Follow steps above
   - Share URL with users

## RentCast API Integration

### Overview

The app includes optional RentCast API integration to supplement internal rent roll data with nationwide market comparables.

### How It Works

1. **Smart Caching:**
   - First API call in an area: Fetches and saves up to 25 comps
   - Subsequent CMAs: Uses cached data (free, no API cost)
   - Cache age tracking: Shows how old cached data is

2. **User Control:**
   - App checks for cached RentCast data
   - User chooses: "Use Cached Data (free)" or "Refresh (1 API call)"
   - Prevents accidental duplicate requests

3. **Data Persistence:**
   - RentCast Terms of Service **allows** storing API data
   - Comps saved to `external_comps` table in SQLite
   - No time limit on cached data retention
   - Geographic radius-based queries

### Setup Instructions

**Step 1: Get Free RentCast API Key**
1. Sign up at https://app.rentcast.io/
2. Navigate to https://app.rentcast.io/app/api
3. Copy your API key
4. Free tier: 50 API requests/month

**Step 2: Add to Streamlit Cloud**
1. Go to your app's Streamlit Cloud dashboard
2. Click "⚙️ Settings" > "Secrets"
3. Add:
   ```toml
   RENTCAST_API_KEY = "your_api_key_here"
   ```
4. Save and redeploy

**Step 3: Verify**
- Generate a CMA in the app
- You should see "🌐 External Market Data (RentCast)" section
- Click "Fetch RentCast Comparables"
- Should return ~25 comps and cache them

### Economics

**Free Tier Efficiency:**
- 50 requests/month × 25 comps = 1,250 cached properties
- After caching: Unlimited CMAs in those areas (no API cost)
- Perfect for single user or small team

**Example Usage:**
- Month 1: Make 10 API calls in 10 different areas = 250 cached comps
- Month 2-12: Use cached data only = 0 API calls
- Result: 10 months of free external data

### Without API Key

The app works perfectly without a RentCast API key:
- Uses only internal rent roll data
- All core CMA features function normally
- User sees "No cached RentCast data" message
- Can still generate comprehensive CMAs from internal data

### Troubleshooting

**"Invalid RentCast API key" error:**
- Double-check API key in Streamlit secrets
- Ensure no extra spaces or quotes
- Verify key is active at https://app.rentcast.io/app/api

**"Rate limit exceeded" error:**
- Free tier: 50 requests/month
- Wait until next month or upgrade plan
- Use cached data in the meantime

**No comps returned:**
- RentCast may not have data for that specific area
- App falls back to internal comps only
- Try a different nearby address

## Support

For deployment issues:
- Streamlit Docs: https://docs.streamlit.io/deploy
- Community Forum: https://discuss.streamlit.io/
- GitHub Issues: Create issue in your repository

For RentCast API issues:
- API Docs: https://developers.rentcast.io/
- Support: Contact via https://www.rentcast.io/

---

**Repository is now clean, optimized, and ready for deployment!** 🚀
