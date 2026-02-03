# CMA Generator - Deployment Guide

## 🚀 Currently Deployed

**Live Demo:** https://cma-generator-k2szbvxthefhkrggxvjblh.streamlit.app/

**Deployment Details:**
- **Platform:** Streamlit Community Cloud (Free Tier)
- **Repository:** https://github.com/projyct/cma-generator
- **Branch:** main
- **Account:** projyct
- **Status:** ✅ Active
- **Deployed:** February 3, 2026
- **Last Updated:** Auto-deploys on push to main branch

**Features:**
- Pre-loaded with 4,738 demo properties (PII removed)
- Geocoded addresses ready for immediate CMA generation
- Mobile-optimized UI (responsive design)
- No authentication required (public demo)

---

## Repository Cleaned for Deployment ✅

The repository has been cleaned and is now ready for deployment to Streamlit Cloud or other hosting platforms.

## Files Remaining (Production Ready)

### Core Application Files:
- **app.py** - Main Streamlit application (41KB)
- **database.py** - SQLite database operations (27KB)
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

3. **Configure Secrets (if needed):**
   - Go to App settings > Secrets
   - Add any environment variables (e.g., API keys)
   - Format:
     ```toml
     GEOCODING_EMAIL = "your_email@example.com"
     ```

4. **Wait for deployment** (2-5 minutes)

5. **Your app is live!**
   - URL will be: `https://your-app-name.streamlit.app`

## Environment Variables

Optional environment variables you can configure in Streamlit Cloud:

```toml
# .streamlit/secrets.toml (on Streamlit Cloud)
GEOCODING_EMAIL = "your_email@example.com"
```

Currently, the app works without any environment variables.

## Database Persistence

### Current Approach: Pre-loaded Database ✅

**The deployed demo includes a pre-populated database in the repository:**
- 4,738 properties with geocoded coordinates
- 4,771 rent records (PII removed)
- Database file: `data/cma_generator.db` (3.4MB)
- Included in Git repository for immediate demo functionality

**Why this approach:**
- Streamlit Cloud has ephemeral storage (resets on restart)
- Geocoding 4,700 addresses takes ~3 minutes (too slow for demo)
- Pre-populated database allows instant CMA generation
- No PII stored (safe for public repository)

**For production deployments:**

**Option 1: External Database (Recommended)**
- Use PostgreSQL, MySQL, or cloud database
- Modify `database.py` to connect to external DB
- Store connection string in secrets

**Option 2: File-based persistence**
- Mount external storage (if supported by hosting platform)
- Use cloud storage (S3, Google Drive API) for database file

**Option 3: Accept ephemeral storage**
- Users re-upload rent roll each session
- Good for testing/demo purposes

The current demo works with the pre-loaded database. Users can also upload their own rent rolls which will be temporarily added to the database until the next restart.

## Application Features

### Current Functionality:
✅ Upload AppFolio rent roll CSV
✅ Parse property data with smart address extraction
✅ Geocode addresses using Census Batch API (143x faster)
✅ Generate CMA reports with comparable properties search
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

## Support

For deployment issues:
- Streamlit Docs: https://docs.streamlit.io/deploy
- Community Forum: https://discuss.streamlit.io/
- GitHub Issues: Create issue in your repository

---

**Repository is now clean, optimized, and ready for deployment!** 🚀
