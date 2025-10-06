# Mobile Service Deployment Update Guide

## Current Issues
1. **Mobile routing not working** - PC service not redirecting mobile users
2. **Static files 404** - Mobile service missing static files
3. **API endpoints wrong** - Missing stock price API, chat API returning 405

## Required Updates

### 1. Update Mobile Service Code
The mobile service needs to be updated with the latest code changes:

```bash
# On the mobile service deployment
git pull origin main  # or whatever branch contains the updates
python manage.py collectstatic --noinput
python manage.py migrate
```

### 2. Environment Variables
Ensure the mobile service has the correct environment variables:

```bash
MOBILE_SERVICE_URL=https://saha-ai-mobile.up.railway.app
DATABASE_URL=<same as PC service>
SECRET_KEY=<same as PC service>
```

### 3. Static Files Issue
The mobile service needs to collect static files:

```bash
python manage.py collectstatic --noinput
```

### 4. API Endpoints
The mobile service needs the updated `advisor/urls.py` and `advisor/views.py` with:
- Stock price API endpoint: `/api/stock-price/<ticker>/`
- Updated chat API to handle GET requests
- Updated portfolio API to handle GET requests

## Deployment Steps

### For Railway Mobile Service:
1. Go to Railway dashboard
2. Select the mobile service
3. Go to "Deployments" tab
4. Click "Redeploy" or trigger a new deployment
5. Ensure environment variables are set correctly

### For Manual Update:
1. SSH into the mobile service
2. Pull latest code
3. Run migrations and collectstatic
4. Restart the service

## Testing After Update
Run the comprehensive test to verify all functionality:

```bash
python test_mobile_app_comprehensive.py
```

Expected results:
- Mobile routing should redirect mobile users (302 status)
- Static files should load (200 status)
- API endpoints should work correctly
- All mobile pages should load properly

## Current Status
- ✅ Mobile device detection middleware updated
- ✅ Stock price API endpoint added
- ✅ API endpoints updated to handle GET requests
- ❌ Mobile service needs deployment update
- ❌ Static files need to be collected on mobile service
- ❌ Environment variables need verification
