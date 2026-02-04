# Google Docs Export - Setup Guide

This guide explains how to enable the "Edit in Google Docs" feature that allows users to export CMA reports directly to their own Google Drive accounts as editable Google Docs.

## Overview

**What it does:**
- Converts HTML CMA reports to native Google Docs format
- Uploads to user's personal Google Drive (not a service account)
- Users can edit, share, and collaborate on reports in Google Docs
- Documents are saved in user's Drive under "My Drive"

**User Experience:**
1. User generates a CMA report in the app
2. User clicks "Connect Google Drive" (one-time OAuth login)
3. User clicks "Create Google Doc" to upload report
4. User clicks link to open and edit document in Google Docs

---

## Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create a new project:**
   - Click "Select a project" dropdown at top
   - Click "New Project"
   - Project name: `CMA Generator` (or your preferred name)
   - Click "Create"

3. **Wait for project creation:**
   - You'll see a notification when the project is ready
   - Select your new project from the dropdown

---

## Step 2: Enable Google Drive API

1. **Navigate to APIs & Services:**
   - In the left sidebar, click "APIs & Services" > "Library"
   - Or visit: https://console.cloud.google.com/apis/library

2. **Search for Google Drive API:**
   - In the search box, type "Google Drive API"
   - Click on "Google Drive API" from results

3. **Enable the API:**
   - Click the blue "Enable" button
   - Wait for API to be enabled (takes a few seconds)

---

## Step 3: Configure OAuth Consent Screen

1. **Navigate to OAuth consent screen:**
   - Left sidebar: "APIs & Services" > "OAuth consent screen"
   - Or visit: https://console.cloud.google.com/apis/credentials/consent

2. **Select User Type:**
   - Choose **"External"** (allows any Google account to authenticate)
   - Click "Create"

3. **Fill out App Information:**
   - **App name:** `CMA Generator`
   - **User support email:** Your email address
   - **App logo:** (optional, leave blank)
   - **Application home page:** Your Streamlit app URL (or leave blank for local)
   - **Authorized domains:** (leave blank for local development)
   - **Developer contact information:** Your email address
   - Click "Save and Continue"

4. **Scopes:**
   - Click "Add or Remove Scopes"
   - Search for: `https://www.googleapis.com/auth/drive.file`
   - Check the box next to this scope
   - Click "Update"
   - Click "Save and Continue"

   **Why this scope?**
   - `drive.file` gives access only to files created by the app
   - App cannot see or modify user's existing Drive files
   - Most secure option for this use case

5. **Test users (if app is in "Testing" mode):**
   - Click "Add Users"
   - Enter email addresses of users who can test the app
   - Click "Add"
   - Click "Save and Continue"

6. **Summary:**
   - Review your settings
   - Click "Back to Dashboard"

---

## Step 4: Create OAuth 2.0 Credentials

1. **Navigate to Credentials:**
   - Left sidebar: "APIs & Services" > "Credentials"
   - Or visit: https://console.cloud.google.com/apis/credentials

2. **Create OAuth Client ID:**
   - Click "Create Credentials" at the top
   - Select "OAuth client ID"

3. **Configure OAuth client:**
   - **Application type:** Web application
   - **Name:** `CMA Generator Web Client`

4. **Authorized redirect URIs:**

   **For local development:**
   ```
   http://localhost:8501
   ```

   **For Streamlit Cloud deployment:**
   ```
   https://your-app-name.streamlit.app
   https://your-app-name.streamlit.app/
   ```

   **Note:** Add both with and without trailing slash for compatibility

5. **Create credentials:**
   - Click "Create"
   - A popup will appear with your credentials

6. **Copy credentials:**
   - **Client ID:** Looks like `123456789-abcdefg.apps.googleusercontent.com`
   - **Client Secret:** Looks like `GOCSPX-aBcDeFgHiJkLmNoPqRsTuVwXyZ`
   - Click "Download JSON" (optional, for backup)
   - Click "OK"

---

## Step 5: Configure Environment Variables

### Local Development (.env file)

1. **Create or edit `.env` file** in your project root:

```bash
# Google Drive Integration (Optional)
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-aBcDeFgHiJkLmNoPqRsTuVwXyZ
GOOGLE_REDIRECT_URI=http://localhost:8501
```

2. **Ensure `.env` is in `.gitignore`:**
   - NEVER commit `.env` to git
   - Check that `.gitignore` includes `.env`

### Streamlit Cloud Deployment

1. **Go to your Streamlit app dashboard:**
   - Visit: https://share.streamlit.io/
   - Click on your app

2. **Open Settings:**
   - Click "⚙️ Settings" (gear icon)
   - Click "Secrets"

3. **Add secrets in TOML format:**

```toml
# Google Drive Integration
GOOGLE_CLIENT_ID = "123456789-abcdefg.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "GOCSPX-aBcDeFgHiJkLmNoPqRsTuVwXyZ"
GOOGLE_REDIRECT_URI = "https://your-app-name.streamlit.app"
```

4. **Important:**
   - Replace `your-app-name` with your actual Streamlit app subdomain
   - Use quotes around values in TOML format
   - No trailing slash in redirect URI

5. **Save and restart app:**
   - Click "Save"
   - App will automatically restart with new secrets

---

## Step 6: Test the Integration

### Local Testing

1. **Start your Streamlit app:**
   ```bash
   streamlit run app.py
   ```

2. **Generate a CMA report:**
   - Navigate to "🔍 Generate CMA"
   - Create a report with comparables

3. **Test Google Docs export:**
   - Scroll to "📝 Edit in Google Docs" section
   - Click "🔐 Connect Google Drive" (if not already connected)
   - Google OAuth login window will open
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - You'll be redirected back to the app
   - Click "📝 Create Google Doc"
   - Report should upload to your Google Drive
   - Click the link to open in Google Docs

### Streamlit Cloud Testing

1. **Deploy to Streamlit Cloud** (if not already deployed)

2. **Important:** Update OAuth redirect URI in Google Cloud Console:
   - Go back to Google Cloud Console > Credentials
   - Edit your OAuth 2.0 Client ID
   - Add production redirect URI: `https://your-app-name.streamlit.app`
   - Save

3. **Test in production:**
   - Visit your Streamlit Cloud app
   - Generate CMA report
   - Test Google Docs export

---

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Problem:** OAuth redirect URI doesn't match what's configured in Google Cloud Console

**Solution:**
1. Check the exact URL in the error message
2. Go to Google Cloud Console > Credentials
3. Edit your OAuth 2.0 Client ID
4. Add the exact redirect URI from the error message
5. Save and try again

**Common mistakes:**
- Missing trailing slash: Add both `https://app.com` AND `https://app.com/`
- HTTP vs HTTPS mismatch
- Wrong subdomain in Streamlit Cloud URL

### Error: "Access blocked: This app's request is invalid"

**Problem:** OAuth consent screen not properly configured

**Solution:**
1. Go to Google Cloud Console > OAuth consent screen
2. Verify all required fields are filled out
3. Add test users if app is in "Testing" mode
4. Verify scopes include `https://www.googleapis.com/auth/drive.file`

### Error: "Google Drive integration not available"

**Problem:** `streamlit-google-auth` package not installed

**Solution:**
```bash
pip install streamlit-google-auth
```

Or ensure it's in `requirements.txt`:
```
streamlit-google-auth>=0.1.0
```

### Error: "Google OAuth not configured"

**Problem:** Missing or incorrect environment variables

**Solution:**
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
2. Check for typos in variable names
3. Ensure secrets are properly formatted (TOML for Streamlit Cloud)
4. Restart app after adding secrets

### Authentication works but upload fails

**Problem:** Google Drive API not enabled or scope issues

**Solution:**
1. Verify Google Drive API is enabled in Google Cloud Console
2. Check that OAuth scope includes `https://www.googleapis.com/auth/drive.file`
3. Revoke and re-authenticate: Click "Disconnect" in app, then reconnect
4. Check app logs for specific error messages

### "File not found" error during upload

**Problem:** HTML file not generated before upload attempt

**Solution:**
- This shouldn't happen in normal use (HTML is generated before upload)
- Check exports directory exists and is writable
- Check app logs for HTML generation errors

---

## Security Considerations

### OAuth Scope: `drive.file`

**What it allows:**
- App can create new files in user's Drive
- App can access only files it created
- App CANNOT see or modify user's existing files

**What it doesn't allow:**
- Reading user's existing Drive files
- Modifying files created by other apps
- Accessing files in shared drives

This is the most secure scope for this use case.

### User Data Privacy

**What's stored:**
- OAuth tokens: Stored in Streamlit session state (memory only)
- Tokens expire when user closes browser or disconnects
- App does NOT store user's Google credentials
- App does NOT store user's Drive files

**What's uploaded:**
- Only CMA reports user explicitly chooses to upload
- Reports contain property data from user's rent roll
- No personal user information is uploaded

### Credential Security

**Best practices:**
1. **NEVER commit credentials to git**
   - Add `.env` to `.gitignore`
   - Use Streamlit secrets for production

2. **Rotate credentials if exposed:**
   - Delete compromised OAuth client in Google Cloud Console
   - Create new credentials
   - Update environment variables

3. **Limit access:**
   - Only add necessary test users in OAuth consent screen
   - Use "External" type only if needed for multiple users

---

## Publishing the App (Optional)

By default, your OAuth consent screen is in "Testing" mode, which means:
- Only test users you explicitly add can authenticate
- No review required from Google
- Perfect for internal/private use

**To allow any Google user to authenticate:**

1. **Go to OAuth consent screen:**
   - https://console.cloud.google.com/apis/credentials/consent

2. **Click "Publish App":**
   - Review warning (app will be available to all Google users)
   - Click "Confirm"

3. **Verification (if required):**
   - Google may require verification if you request sensitive scopes
   - `drive.file` scope typically doesn't require verification
   - If prompted, follow Google's verification process

**Recommendation for this app:**
- Keep app in "Testing" mode
- Add only authorized users as test users
- More secure for internal property management use

---

## Maintenance

### Monitoring Usage

**Google Cloud Console:**
- View API usage: APIs & Services > Dashboard
- Monitor quota: APIs & Services > Quotas
- View OAuth grants: Security > OAuth consent screen

**Free tier limits:**
- Google Drive API: 1 billion requests/day (plenty for this app)
- No cost for API usage
- OAuth login: Unlimited, free

### Updating Credentials

**If you need to rotate credentials:**
1. Create new OAuth 2.0 Client ID in Google Cloud Console
2. Update environment variables with new credentials
3. Delete old OAuth client in Google Cloud Console
4. Users will need to reconnect their Google accounts

### Revoking Access

**Users can revoke app access:**
1. Go to https://myaccount.google.com/permissions
2. Find "CMA Generator" in list
3. Click "Remove Access"
4. User will need to reconnect to use Google Docs export again

---

## Cost

**Total cost: $0**

- Google Drive API: Free (within generous quotas)
- Google Cloud Project: Free (no compute resources used)
- OAuth authentication: Free (unlimited)
- File storage: Uses user's own Google Drive quota (not your quota)

**No credit card required** for this integration.

---

## Support

**Google Cloud Documentation:**
- OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
- Drive API: https://developers.google.com/drive/api/guides/about-sdk

**Common issues:**
- Check Google Cloud Console > APIs & Services > Credentials
- Verify OAuth consent screen is properly configured
- Check app logs in Streamlit Cloud dashboard
- Test locally before deploying to production

---

## Summary Checklist

- [ ] Create Google Cloud project
- [ ] Enable Google Drive API
- [ ] Configure OAuth consent screen
- [ ] Create OAuth 2.0 credentials
- [ ] Add credentials to `.env` (local) or Streamlit secrets (cloud)
- [ ] Add redirect URI to Google Cloud Console
- [ ] Test authentication flow
- [ ] Test document upload
- [ ] Verify document appears in user's Google Drive
- [ ] Test editing document in Google Docs

**Estimated setup time:** 10-15 minutes

---

**Questions?** Check the troubleshooting section above or review Google Cloud Console settings.
