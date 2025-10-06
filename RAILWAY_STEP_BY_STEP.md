# 🚂 Railway Deployment - Step-by-Step Guide

## 🎯 **Current Status:**
- ✅ **main branch**: PC version with device routing (pushed to GitHub)
- ✅ **mobile branch**: Mobile version only (pushed to GitHub)
- ✅ **Device detection**: Implemented and ready

## 🚀 **Step-by-Step Railway Deployment**

### **Step 1: Add Mobile Service in Railway**

1. **Go to your Railway dashboard**
2. **Click the "+" button** next to "Add New Service"
3. **Select "GitHub Repo"** from the dropdown
4. **Configure the Mobile Service:**
   ```
   Repository: nithin1906/saha-ai (your repo)
   Branch: mobile
   Service Name: mobile
   ```

### **Step 2: Configure Mobile Service Environment Variables**

In the mobile service settings, add these environment variables:

```
SECRET_KEY=your-production-secret-key
DEBUG=False
IS_MOBILE_DEPLOYMENT=True
DATABASE_URL=postgresql://... (same as your PC service)
```

### **Step 3: Update PC Service Environment Variables**

In your existing PC service settings, add this environment variable:

```
MOBILE_SERVICE_URL=https://your-mobile-service-name.up.railway.app
```

### **Step 4: Deploy Both Services**

1. **PC Service**: Will auto-deploy from `main` branch
2. **Mobile Service**: Will auto-deploy from `mobile` branch

### **Step 5: Test Device Detection**

1. **Desktop Test**: Visit your PC service URL
   - Should show PC version
   - No redirects

2. **Mobile Test**: Visit your PC service URL from mobile device
   - Should redirect to mobile service URL
   - Should show mobile version

## 🔧 **Detailed Configuration**

### **PC Service (Existing)**
```
Service Name: web (or your existing name)
Branch: main
URL: saha-ai.up.railway.app
Environment Variables:
- SECRET_KEY=your-secret
- DEBUG=False
- MOBILE_SERVICE_URL=https://your-mobile-service.up.railway.app
- DATABASE_URL=postgresql://...
```

### **Mobile Service (New)**
```
Service Name: mobile
Branch: mobile
URL: saha-ai-mobile.up.railway.app (or similar)
Environment Variables:
- SECRET_KEY=your-secret
- DEBUG=False
- IS_MOBILE_DEPLOYMENT=True
- DATABASE_URL=postgresql://... (same as PC)
```

## 🎯 **What Happens After Deployment**

### **Desktop Users:**
1. Visit `saha-ai.up.railway.app`
2. PC service detects desktop device
3. Serves PC version (unchanged experience)

### **Mobile Users:**
1. Visit `saha-ai.up.railway.app`
2. PC service detects mobile device
3. **Automatically redirects** to `saha-ai-mobile.up.railway.app`
4. Mobile service serves mobile version

## 🛡️ **Safety Benefits**

- ✅ **PC version stable** - main branch never touched
- ✅ **Mobile version isolated** - mobile branch separate
- ✅ **Independent deployments** - deploy mobile without affecting PC
- ✅ **Easy rollbacks** - rollback mobile without affecting PC

## 🚨 **Important Notes**

1. **Database**: Both services will use the same database
2. **Environment Variables**: Use the same SECRET_KEY and DATABASE_URL
3. **Mobile Service URL**: Update PC service with mobile service URL after deployment
4. **Testing**: Test both versions after deployment

## 🎉 **Ready to Deploy!**

Both branches are ready:
- **main branch**: PC version with device routing
- **mobile branch**: Mobile version only

**Next Action**: Add Mobile Service in Railway dashboard!
