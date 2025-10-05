# Railway Deployment Configuration

## 🚀 **Railway Deployment Steps**

### **1. Environment Variables**
Set these in Railway dashboard:

```
SECRET_KEY=your-production-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### **2. Production Settings**
Railway will automatically use `settings_production.py` when deployed.

### **3. Static Files**
Railway will automatically collect and serve static files.

### **4. Database**
Railway provides PostgreSQL database automatically.

## 📱 **Device Detection Features**

### **Automatic Detection**
- Mobile devices get mobile version
- Desktop devices get PC version
- Same URLs, different content

### **Manual Override**
- `?mobile=1` - Force mobile version
- `?desktop=1` - Force desktop version
- Preference stored in session

### **URL Structure**
- `https://your-app.railway.app/` - Auto-detects device
- `https://your-app.railway.app/mobile/` - Direct mobile access
- `https://your-app.railway.app/profile/` - Auto-detects device

## 🔧 **Deployment Commands**

Railway will automatically run:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## ✅ **Ready for Deployment**

1. Push code to GitHub
2. Railway automatically deploys
3. Set environment variables
4. Test both versions

The app will automatically serve the appropriate version based on device detection!
