# Railway Deployment Fix Guide

## Issues Fixed

### 1. Middleware Order Issue ✅
**Problem**: Custom middleware was running before Django's `AuthenticationMiddleware`, causing `AttributeError: 'WSGIRequest' object has no attribute 'user'`

**Fix**: Reordered middleware in `core/settings_production.py` so that authentication middleware runs first:
```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Must come before custom middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'users.middleware.SecurityLoggingMiddleware',  # Now has access to request.user
    'users.middleware.InviteOnlyMiddleware',  # Now has access to request.user
]
```

### 2. Health Check Endpoint Issue ✅
**Problem**: `/health` endpoint was going through authentication middleware, causing errors during health checks

**Fix**: Updated both custom middleware classes to skip the health check endpoint:
```python
# In users/middleware.py
def process_request(self, request):
    # Skip logging for health check endpoint
    if request.path == '/health/':
        return None
    # ... rest of the middleware logic
```

### 3. Database Connection Issue 🔧
**Problem**: Migrations were failing with `connection to server at "localhost" (::1), port 5432 failed`

**Potential Causes**:
- `DATABASE_URL` environment variable not set in Railway
- PostgreSQL service not properly linked to the app
- Database credentials not correctly configured

## Railway Configuration Required

### Step 1: Add PostgreSQL Database
1. Go to your Railway project
2. Click "New" → "Database" → "Add PostgreSQL"
3. Railway will automatically provision a PostgreSQL instance

### Step 2: Link Database to Your App
1. In your Railway project, click on your app service
2. Go to "Variables" tab
3. Verify that `DATABASE_URL` is set (it should be automatically added when you link the database)
4. The format should be: `postgresql://user:password@host:port/database`

### Step 3: Set Required Environment Variables
Make sure these variables are set in Railway:

**Required:**
- `DATABASE_URL` - Should be auto-set when PostgreSQL is added
- `SECRET_KEY` - A secure random string (generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DJANGO_SETTINGS_MODULE` - Set to `core.settings_production`

**Optional but Recommended:**
- `ALLOWED_HOSTS` - Your Railway domain (e.g., `your-app.up.railway.app`)
- `PORT` - Usually auto-set by Railway (default: 8000)

### Step 4: Verify Service Configuration
1. Make sure your Railway service is using:
   - Start Command: `bash start.sh`
   - Build Command: `bash build.sh` (optional)
2. Health check path: `/health`
3. Health check timeout: 300 seconds

## Testing Locally

To test these fixes locally with a PostgreSQL database:

```bash
# Set environment variables
export DJANGO_SETTINGS_MODULE=core.settings_production
export DATABASE_URL="postgresql://user:password@localhost:5432/yourdb"
export SECRET_KEY="your-secret-key-here"

# Run migrations
python manage.py migrate

# Test the server
python manage.py runserver
```

## Deployment Steps

1. **Commit and Push Changes**:
   ```bash
   git add .
   git commit -m "Fix Railway deployment issues: middleware order and health check"
   git push origin main
   ```

2. **Verify Railway Settings**:
   - Check that PostgreSQL is added and running
   - Verify all environment variables are set
   - Check that the app is linked to the database

3. **Trigger Deployment**:
   - Railway should auto-deploy on push
   - Or manually trigger deployment from Railway dashboard

4. **Monitor Logs**:
   - Watch the deployment logs in Railway
   - Look for successful migration completion
   - Check that Gunicorn starts without errors
   - Verify health checks are passing

## Common Issues and Solutions

### Issue: "DATABASE_URL is not set"
**Solution**: 
- Add PostgreSQL to your Railway project
- Verify the database service is running
- Check that your app service has access to the database service variables

### Issue: "relation does not exist" errors
**Solution**: 
- Migrations haven't run successfully
- Check that migrations complete during the start.sh phase
- Manually trigger migrations: `python manage.py migrate` in Railway's console

### Issue: Health check failing
**Solution**: 
- Make sure `/health` endpoint is accessible
- Check that middleware is not blocking the endpoint
- Increase health check timeout in railway.json if needed

### Issue: Static files not loading
**Solution**: 
- Ensure `python manage.py collectstatic` runs in start.sh
- Verify `STATIC_ROOT` is set correctly
- Check that WhiteNoise middleware is properly configured

## Verification Checklist

After deployment, verify:
- [ ] App is accessible at Railway URL
- [ ] Health check endpoint returns `{"status": "healthy", "message": "SAHA-AI is running"}`
- [ ] Database connection is working (no migration errors in logs)
- [ ] Static files are loading correctly
- [ ] Authentication works (can log in/out)
- [ ] No `AttributeError` in logs related to `request.user`

## Need More Help?

If you're still experiencing issues:
1. Check Railway logs for specific error messages
2. Verify all environment variables are properly set
3. Ensure PostgreSQL service is running and linked
4. Check that your Railway plan supports the resources you're using

## Files Modified

- `core/settings_production.py` - Fixed middleware order
- `users/middleware.py` - Added health check endpoint skip
- `start.sh` - Improved error handling and database checks
- `build.sh` - Simplified build process

