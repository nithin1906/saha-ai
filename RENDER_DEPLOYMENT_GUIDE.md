# 🚀 Render Deployment Guide (FREE FOREVER)

## **Why Render?**
- ✅ **Free tier never expires**
- ✅ **750 hours/month** (24/7 coverage)
- ✅ **PostgreSQL database included**
- ✅ **Automatic GitHub deployments**
- ✅ **Custom domains supported**

## **Step-by-Step Render Deployment**

### **Step 1: Sign Up**
1. Go to [render.com](https://render.com)
2. **Sign up with GitHub**
3. **Connect your SAHA-AI repository**

### **Step 2: Create Database**
1. **Click "New +"** → **"PostgreSQL"**
2. **Name:** `saha-ai-db`
3. **Plan:** Free
4. **Click "Create Database"**
5. **Copy the connection string** (you'll need this)

### **Step 3: Create Web Service**
1. **Click "New +"** → **"Web Service"**
2. **Connect Repository:** Select your SAHA-AI repo
3. **Configure:**
   - **Name:** `saha-ai-web`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`

### **Step 4: Set Environment Variables**
In your web service settings, add:

```bash
SECRET_KEY=M3d0-H-c9CFw0zhZoH4tp_fkOZ3eJg7HNhfqKu3z-Y2j6AFbweIpldfjbLfj_4pvwWM
DEBUG=False
ALLOWED_HOSTS=saha-ai-web.onrender.com
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### **Step 5: Deploy**
1. **Click "Create Web Service"**
2. **Render will automatically deploy**
3. **Your app will be live at:** `https://saha-ai-web.onrender.com`

## **Post-Deployment Setup**

Once deployed, run these commands in Render's console:

```bash
python manage.py migrate
python manage.py shell -c "
from django.contrib.auth.models import User
from users.models import UserProfile, InviteCode
from django.utils import timezone
from datetime import timedelta

# Create admin
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

## **Render vs Railway Comparison**

| Feature | Railway | Render |
|---------|---------|--------|
| **Free Tier** | 30 days | Forever |
| **Monthly Hours** | $5 credit | 750 hours |
| **Database** | PostgreSQL | PostgreSQL |
| **Custom Domain** | ✅ | ✅ |
| **Auto Deploy** | ✅ | ✅ |
| **Cost After Trial** | $5/month | Free |

## **Migration Strategy**

### **Option A: Start Fresh on Render**
1. **Deploy to Render** (free forever)
2. **Keep Railway** for testing/development
3. **Switch to Render** for production

### **Option B: Upgrade Railway**
1. **Pay $5/month** for Railway
2. **Keep everything as-is**
3. **More features** (better performance, support)

### **Option C: Hybrid Approach**
1. **Use Railway** for development/testing
2. **Use Render** for production
3. **Best of both worlds**

## **My Recommendation**

**Start with Render** because:
- ✅ **Truly free forever**
- ✅ **Same features as Railway**
- ✅ **Easy migration**
- ✅ **No surprise bills**

**You can always switch back to Railway later** if you want more features!

---

**Ready to deploy to Render? It's free forever! 🎯**
