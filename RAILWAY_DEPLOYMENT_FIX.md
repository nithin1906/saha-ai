# Railway Deployment Guide - Fixed Version

## 🚀 Railway Deployment Fix Summary

This guide addresses the Railway deployment error that was occurring due to incompatible package versions, specifically the `pandas-ta==0.3.14b0` package that doesn't exist on PyPI.

## 🔧 Issues Fixed

### 1. **Primary Issue: pandas-ta Package**
- **Problem**: `pandas-ta==0.3.14b0` doesn't exist on PyPI
- **Solution**: Updated to `pandas-ta>=0.3.0,<0.4.0` to allow pip to find a compatible version

### 2. **Python Version Compatibility**
- **Problem**: Some packages required Python 3.12+ but Railway was using Python 3.11
- **Solution**: Updated `runtime.txt` to Python 3.11.10 and created `nixpacks.toml` for better control

### 3. **Railway Configuration**
- **Problem**: Basic Railway configuration
- **Solution**: Enhanced `railway.json` with better gunicorn settings and created `nixpacks.toml`

### 4. **Django Settings**
- **Problem**: Production settings not optimized for Railway
- **Solution**: Updated `settings_production.py` to use Railway's DATABASE_URL and handle Railway domains

## 📁 Files Modified

### 1. `requirements.txt`
```txt
# Core Django packages
Django==5.0.6
djangorestframework==3.15.1
django-cors-headers==4.3.1

# Database packages
psycopg2-binary==2.9.9
dj-database-url==2.1.0

# Data processing packages
numpy==1.24.3
pandas==2.0.3
pandas-ta>=0.3.0,<0.4.0  # Fixed: was 0.3.14b0 (doesn't exist)
scikit-learn==1.3.0
joblib==1.4.2

# Web scraping and API packages
requests==2.31.0
beautifulsoup4==4.12.3
gnews==0.2.6
yfinance==0.2.38

# NLP packages
nltk==3.8.1

# Configuration packages
python-decouple==3.8

# Production server packages
gunicorn==21.2.0
whitenoise==6.6.0

# Build tools
setuptools==69.5.1
```

### 2. `runtime.txt`
```
python-3.11.10
```

### 3. `nixpacks.toml` (New File)
```toml
[phases.setup]
nixPkgs = ["python311", "postgresql_16.dev", "gcc"]

[phases.install]
cmds = [
    "python -m venv --copies /opt/venv",
    ". /opt/venv/bin/activate",
    "pip install --upgrade pip",
    "pip install -r requirements.txt"
]

[start]
cmd = "gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120"
```

### 4. `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --max-requests 1000 --max-requests-jitter 100",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 5. `core/settings_production.py`
- Updated to use Railway's DATABASE_URL
- Added Railway domain handling for ALLOWED_HOSTS
- Enhanced database configuration with connection pooling

## 🚀 Deployment Steps

### 1. **Commit Changes**
```bash
git add .
git commit -m "Fix Railway deployment: Update pandas-ta and configuration"
git push origin main
```

### 2. **Railway Environment Variables**
Set these environment variables in your Railway project:

```bash
# Required
SECRET_KEY=your-secret-key-here
DEBUG=False
DJANGO_SETTINGS_MODULE=core.settings_production

# Optional (Railway will auto-provide DATABASE_URL)
ALLOWED_HOSTS=your-domain.railway.app,localhost,127.0.0.1
```

### 3. **Database Setup**
Railway will automatically provide a PostgreSQL database and set the `DATABASE_URL` environment variable.

### 4. **Deploy**
Railway will automatically detect the changes and redeploy. Monitor the deployment logs for success.

## 🔍 Verification Steps

### 1. **Check Build Logs**
- Ensure `pandas-ta` installs successfully
- Verify all dependencies are installed
- Check that gunicorn starts correctly

### 2. **Test Application**
- Visit your Railway domain
- Test database connectivity
- Verify static files are served correctly

### 3. **Monitor Performance**
- Check Railway metrics
- Monitor memory usage
- Verify response times

## 🛠️ Troubleshooting

### If pandas-ta still fails:
1. Check PyPI for latest compatible versions
2. Consider using `pandas-ta` without version pinning
3. Verify Python version compatibility

### If database connection fails:
1. Check DATABASE_URL environment variable
2. Verify PostgreSQL service is running
3. Check database credentials

### If static files don't load:
1. Run `python manage.py collectstatic` locally
2. Check STATIC_ROOT configuration
3. Verify whitenoise middleware is enabled

## 📊 Performance Optimizations

### Gunicorn Settings
- `--workers 3`: Optimal for Railway's memory limits
- `--timeout 120`: Prevents timeout on long requests
- `--max-requests 1000`: Prevents memory leaks
- `--max-requests-jitter 100`: Prevents thundering herd

### Database Settings
- `conn_max_age=600`: Reuse connections for 10 minutes
- `conn_health_checks=True`: Verify connections before use

## 🔒 Security Considerations

1. **Environment Variables**: Never commit secrets to git
2. **DEBUG**: Always False in production
3. **ALLOWED_HOSTS**: Restrict to your domains
4. **HTTPS**: Railway provides SSL certificates automatically

## 📈 Monitoring

Railway provides built-in monitoring for:
- CPU usage
- Memory consumption
- Network traffic
- Error rates
- Response times

## 🎯 Next Steps

1. **Deploy**: Push changes and monitor deployment
2. **Test**: Verify all functionality works
3. **Monitor**: Watch performance metrics
4. **Scale**: Adjust resources as needed

---

**Note**: This fix addresses the specific Railway deployment error you encountered. The main issue was the non-existent `pandas-ta==0.3.14b0` package, which has been resolved by using a version range that allows pip to find a compatible version.
