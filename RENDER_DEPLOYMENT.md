## Render Deployment Checklist

This guide will walk you through deploying your Cakemallow backend to Render.

### Step 1: Prepare Your Repository ✅

- [x] Created `Procfile` — tells Render how to start the app
- [x] Created `render.yaml` — defines services and build commands
- [x] Updated `requirements.txt` — added `psycopg2-binary`, `whitenoise`, `dj-database-url`
- [x] Updated `settings.py` — configured for PostgreSQL, static files, and production security

**Push these changes:**

```bash
git add Procfile render.yaml requirements.txt cakemallow_backend/settings.py
git commit -m "Add Render deployment configuration"
git push
```

---

### Step 2: Create Render Account

1. Go to https://render.com (sign up for free account)
2. Connect your GitHub repository

---

### Step 3: Create PostgreSQL Database

1. In Render dashboard: **New → PostgreSQL**
   - **Name:** `cakemallow-db`
   - **Database Name:** `cakemallow_db`
   - **Database User:** `cakemallow_user`
   - **Region:** Choose nearest to you (e.g., Oregon for US)
   - **Plan:** Free
   - Click **Create Database**

2. **Copy the DATABASE_URL** from the database's Info page (you'll need it for the web service)

---

### Step 4: Create Web Service

1. In Render dashboard: **New → Web Service**
   - Select your **GitHub repository**
   - **Name:** `cakemallow-backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn cakemallow_backend.wsgi`
   - **Plan:** Free

---

### Step 5: Set Environment Variables

In the Web Service settings, go to **Environment** and add:

| Key                        | Value                                         | Notes                                        |
| -------------------------- | --------------------------------------------- | -------------------------------------------- |
| `DEBUG`                    | `False`                                       | **CRITICAL** — never True in production      |
| `SECRET_KEY`               | Generate a strong one\*                       | Use 50+ random characters                    |
| `ALLOWED_HOSTS`            | `yourdomain.onrender.com`                     | Or your custom domain                        |
| `DATABASE_URL`             | Paste from PostgreSQL database                | Render will auto-create this, just select it |
| `CORS_ALLOWED_ORIGINS`     | `https://your-frontend.com`                   | Your frontend URL (https)                    |
| `EMAIL_BACKEND`            | `django.core.mail.backends.smtp.EmailBackend` | For production emails                        |
| `EMAIL_HOST`               | `smtp.gmail.com`                              | Or your email provider                       |
| `EMAIL_PORT`               | `587`                                         |                                              |
| `EMAIL_HOST_USER`          | your-email@gmail.com                          |                                              |
| `EMAIL_HOST_PASSWORD`      | Your app password\*\*                         |                                              |
| `DEFAULT_FROM_EMAIL`       | `Cakemallow <noreply@cakemallow.com>`         |                                              |
| `RAZORPAY_KEY_ID`          | Your Razorpay live key                        | From Razorpay dashboard                      |
| `RAZORPAY_KEY_SECRET`      | Your Razorpay secret                          | From Razorpay dashboard                      |
| `RAZORPAY_WEBHOOK_SECRET`  | Your webhook secret                           |                                              |
| `FAST2SMS_API_KEY`         | Your API key                                  | If using SMS                                 |
| `WHATSAPP_PROVIDER`        | `gupshup` or `aisensy`                        |                                              |
| `GUPSHUP_API_KEY`          | Your key                                      | (if using Gupshup)                           |
| `GUPSHUP_SOURCE`           | Your phone number                             | (if using Gupshup)                           |
| `FCM_SERVICE_ACCOUNT_FILE` | Base64 encoded key\*\*\*                      | (optional, for push notifications)           |
| `REDIS_URL`                | Upstash Redis URL                             | (optional, if using Celery)                  |

**\* Generate SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**\*\* Gmail App Password:**

1. Enable 2FA on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Select Mail + Windows/Linux/Mac
4. Copy the generated password (16 chars, no spaces)

**\*\*\* FCM Service Account (optional):**
If using Firebase Cloud Messaging for push notifications:

1. Download the JSON key from Firebase Console
2. Base64 encode it: `cat key.json | base64`
3. Paste the output as `FCM_SERVICE_ACCOUNT_FILE` env var

---

### Step 6: Connect Database to Web Service

1. In **Web Service Environment Tab**, you should see `DATABASE_URL` already listed (Render auto-creates this for linked PostgreSQL databases)
2. If not, manually add it:
   - Key: `DATABASE_URL`
   - Value: Copy from PostgreSQL database Info page

---

### Step 7: Deploy

1. Click **Create Web Service** — this will trigger the first build
2. **Wait for build to complete** (5-10 minutes)
3. Check the **Logs** tab for any errors
4. **Common issues:**
   - ❌ `ImportError: No module named dj_database_url` → Run: `pip install dj-database-url`
   - ❌ `django.db.utils.OperationalError: FATAL: password authentication failed` → Check `DATABASE_URL`
   - ❌ `ModuleNotFoundError: No module named 'whitenoise'` → Run: `pip install whitenoise`

---

### Step 8: Verify Deployment

Once the build succeeds:

```bash
# Your API will be at:
https://cakemallow-backend.onrender.com/

# Test endpoints:
curl https://cakemallow-backend.onrender.com/api/health/
curl https://cakemallow-backend.onrender.com/api/products/
```

Check the **Logs** tab in Render for any runtime errors.

---

### Step 9 (Optional): Add Custom Domain

1. Go to Web Service → **Settings → Custom Domain**
2. Add your domain (e.g., `api.yourdomain.com`)
3. Update DNS records at your domain provider (Render will show exact values)
4. Update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` env vars

---

### Step 10 (Optional): Setup Celery/Redis

If you're using Celery for background tasks:

1. Create **Upstash Redis** (free tier):
   - Go to https://upstash.com
   - Create a Redis database
   - Copy the `REDIS_URL` (use `rediss://` with double-s for TLS)

2. Add to Web Service env vars:
   - `REDIS_URL` = Upstash Redis URL

3. Create another **Web Service** for Celery worker:
   - Same repo, same env vars
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `celery -A cakemallow_backend worker -l info`
   - **Type:** `Background`

---

### Troubleshooting

| Problem                               | Solution                                                                |
| ------------------------------------- | ----------------------------------------------------------------------- |
| Build fails with `pip install` errors | Check `requirements.txt` syntax and versions                            |
| App crashes on startup                | Check **Logs** tab → look for import/config errors                      |
| Static files return 404               | Run: `python manage.py collectstatic --noinput` locally first           |
| Database connection fails             | Verify `DATABASE_URL` env var is set correctly                          |
| CORS errors                           | Update `CORS_ALLOWED_ORIGINS` env var with correct frontend URL (https) |
| Email not sending                     | Check `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`            |

---

### Documentation Links

- [Render Django Deployment Guide](https://render.com/docs/deploy-django)
- [Whitenoise Documentation](https://whitenoise.readthedocs.io/)
- [dj-database-url Docs](https://github.com/adamchainz/dj-database-url)
- [Upstash Redis](https://upstash.com)

---

**Your app is ready to deploy! Follow the steps above in order.** 🚀
