# 🚀 SAHA-AI Deployment Guide

## **Quick Deploy Options**

### **Option 1: Railway (Recommended - Easiest)**
1. **Sign up** at [railway.app](https://railway.app)
2. **Connect GitHub** and select your SAHA-AI repository
3. **Add PostgreSQL** database service
4. **Set Environment Variables:**
   ```
   SECRET_KEY=your-super-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.railway.app
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   ```
5. **Deploy** - Railway auto-detects Django and deploys!

### **Option 2: Render (Free Tier)**
1. **Sign up** at [render.com](https://render.com)
2. **Create Web Service** from GitHub
3. **Add PostgreSQL** database
4. **Configure:**
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`
5. **Set Environment Variables** (same as Railway)
6. **Deploy**

### **Option 3: Heroku (Paid)**
1. **Install Heroku CLI**
2. **Login:** `heroku login`
3. **Create app:** `heroku create your-app-name`
4. **Add PostgreSQL:** `heroku addons:create heroku-postgresql:mini`
5. **Set config vars:** `heroku config:set SECRET_KEY=your-key DEBUG=False`
6. **Deploy:** `git push heroku main`

## **Environment Variables Setup**

### **Required Variables:**
```bash
SECRET_KEY=your-super-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### **Optional Variables:**
```bash
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

## **Pre-Deployment Checklist**

### **✅ Code Preparation:**
- [ ] All files committed to Git
- [ ] `requirements.txt` updated
- [ ] `Procfile` configured
- [ ] Static files ready
- [ ] Database migrations ready

### **✅ Security:**
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` configured
- [ ] HTTPS enabled (if using custom domain)

### **✅ Database:**
- [ ] PostgreSQL database provisioned
- [ ] `DATABASE_URL` configured
- [ ] Migrations ready to run

## **Post-Deployment Setup**

### **1. Run Initial Setup:**
```bash
# SSH into your deployment platform or use their console
python manage.py migrate
python manage.py collectstatic --noinput
```

### **2. Create Admin User:**
```bash
python manage.py shell -c "
from django.contrib.auth.models import User
from users.models import UserProfile, InviteCode
from django.utils import timezone
from datetime import timedelta

# Create admin if not exists
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@saha-ai.com', 'Nithin#1906')
    UserProfile.objects.create(user=admin, is_approved=True)
    print('✅ Admin created')

# Generate invite codes
for i in range(10):
    InviteCode.objects.create(
        created_by=admin,
        expires_at=timezone.now() + timedelta(days=30),
        max_uses=5
    )
print('✅ Invite codes generated')
"
```

### **3. Test Your Deployment:**
- [ ] Visit your app URL
- [ ] Test login with admin credentials
- [ ] Access admin dashboard
- [ ] Test user registration with invite code
- [ ] Test stock/mutual fund analysis

## **Troubleshooting**

### **Common Issues:**

#### **"DisallowedHost" Error:**
- Add your domain to `ALLOWED_HOSTS`
- Use `ALLOWED_HOSTS=*` for testing (not recommended for production)

#### **Static Files Not Loading:**
- Run `python manage.py collectstatic --noinput`
- Check `STATIC_ROOT` and `STATIC_URL` settings

#### **Database Connection Error:**
- Verify `DATABASE_URL` format
- Check database service is running
- Ensure migrations are applied

#### **Import Errors:**
- Check `requirements.txt` has all dependencies
- Verify Python version compatibility

### **Performance Optimization:**
- Use CDN for static files
- Enable database connection pooling
- Configure caching (Redis)
- Use production WSGI server (Gunicorn)

## **Monitoring & Maintenance**

### **Logs:**
- Check deployment platform logs
- Monitor error rates
- Set up alerts for downtime

### **Updates:**
- Regular security updates
- Database backups
- Performance monitoring

---

## **🎯 Quick Start Commands**

```bash
# Local testing
python manage.py runserver

# Production setup
chmod +x deploy_setup.sh
./deploy_setup.sh

# Deploy to Railway
railway login
railway link
railway up

# Deploy to Render
# Use their web interface with render.yaml

# Deploy to Heroku
heroku create your-app-name
git push heroku main
```

**Your SAHA-AI is ready for production! 🚀**