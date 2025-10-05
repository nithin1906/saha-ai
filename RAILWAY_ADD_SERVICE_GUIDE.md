# 🚂 Railway "Add New Service" Guide

## 🎯 **What You're Seeing in Railway Dashboard**

From your Railway dashboard, I can see:
- **Project**: "fearless-respect" 
- **Current Service**: "web" (your PC version)
- **URL**: `saha-ai.up.railway.app`
- **Add New Service**: Available with dropdown options

## 🚀 **Step-by-Step Guide to Add Mobile Service**

### **Step 1: Click "Add New Service"**
1. In your Railway dashboard, click the **"+" button** next to "Add New Service"
2. Select **"GitHub Repo"** from the dropdown

### **Step 2: Configure New Service**
1. **Repository**: Select your existing GitHub repository (same one as PC version)
2. **Service Name**: Name it `mobile` or `web-mobile`
3. **Branch**: Use `main` (same branch as PC version)

### **Step 3: Environment Variables**
Railway will ask for environment variables. Set these:

```
SECRET_KEY=your-production-secret-key
DEBUG=False
IS_MOBILE_DEPLOYMENT=True
DATABASE_URL=postgresql://... (same as PC version)
```

### **Step 4: Build Configuration**
Railway will auto-detect Django, but you can customize:

**Build Command**: `python manage.py collectstatic --noinput`
**Start Command**: `python manage.py runserver 0.0.0.0:$PORT`

## 🔧 **Code Changes Needed**

### **1. Update Settings for Mobile Detection**
```python
# settings.py
IS_MOBILE_DEPLOYMENT = os.environ.get('IS_MOBILE_DEPLOYMENT', False)

# In your views
def index(request):
    if IS_MOBILE_DEPLOYMENT or getattr(request, 'is_mobile', False):
        return render(request, 'advisor/mobile_index.html')
    else:
        return render(request, 'advisor/index.html')
```

### **2. Update PC Version for Mobile Redirect**
```python
# In PC version views
def index(request):
    if getattr(request, 'is_mobile', False):
        return redirect('https://your-mobile-service.railway.app/')
    else:
        return render(request, 'advisor/index.html')
```

## 📱 **What Happens After Deployment**

### **Service 1: PC Version (Existing)**
- **URL**: `saha-ai.up.railway.app` (unchanged)
- **Code**: PC version only
- **Status**: Stable, untouched

### **Service 2: Mobile Version (New)**
- **URL**: `saha-ai-mobile.up.railway.app` (new)
- **Code**: Mobile version only
- **Status**: New, can be tested safely

## 🎯 **Deployment Architecture**

```
Railway Project: "fearless-respect"
├── Service: web (existing)
│   ├── URL: saha-ai.up.railway.app
│   ├── Code: PC version
│   └── Status: Stable
├── Service: mobile (new)
│   ├── URL: saha-ai-mobile.up.railway.app
│   ├── Code: Mobile version
│   └── Status: New, testable
└── Database: Postgres (shared)
```

## 🔄 **User Flow**

### **Desktop Users**
1. Visit `saha-ai.up.railway.app`
2. Get PC version (unchanged experience)

### **Mobile Users**
1. Visit `saha-ai.up.railway.app`
2. PC version detects mobile device
3. Redirects to `saha-ai-mobile.up.railway.app`
4. Get mobile version

## 🛡️ **Safety Benefits**

- ✅ **PC version stays stable** - no risk to existing users
- ✅ **Mobile version isolated** - can test safely
- ✅ **Independent deployments** - deploy mobile without touching PC
- ✅ **Easy rollbacks** - rollback mobile without affecting PC

## 🚀 **Next Steps**

1. **Click "Add New Service"** in Railway
2. **Select "GitHub Repo"**
3. **Configure environment variables**
4. **Deploy mobile service**
5. **Test both versions**

This gives you the safest deployment approach with complete isolation between PC and mobile versions!
