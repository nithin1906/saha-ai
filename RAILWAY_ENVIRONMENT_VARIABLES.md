# 🔑 Railway Environment Variables - Where to Find Values

## 📋 **Environment Variables Guide**

### **1. DATABASE_URL - Which One to Use?**

#### **Use DATABASE_URL (Not Public URL)**
```
✅ Use: DATABASE_URL
❌ Don't use: DATABASE_PUBLIC_URL
```

**Why?**
- `DATABASE_URL` is the internal connection string for your app
- `DATABASE_PUBLIC_URL` is for external connections (not needed for your app)

#### **Where to Find DATABASE_URL:**
1. **Go to your Railway dashboard**
2. **Click on your Postgres service**
3. **Go to "Variables" tab**
4. **Copy the value of `DATABASE_URL`**

### **2. SECRET_KEY - Where to Find It?**

#### **Option 1: Use Existing SECRET_KEY**
1. **Go to your existing PC service**
2. **Click "Variables" tab**
3. **Copy the value of `SECRET_KEY`**

#### **Option 2: Generate New SECRET_KEY**
If you need a new one, you can generate it:

```python
# Run this in Python to generate a new secret key
import secrets
print(secrets.token_urlsafe(50))
```

### **3. Complete Environment Variables Setup**

#### **For Mobile Service:**
```
SECRET_KEY=your-existing-secret-key-from-pc-service
DEBUG=False
IS_MOBILE_DEPLOYMENT=True
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

#### **For PC Service (Add This):**
```
MOBILE_SERVICE_URL=https://your-mobile-service-name.up.railway.app
```

## 🔍 **Step-by-Step: Finding Your Values**

### **Step 1: Find DATABASE_URL**
1. **Railway Dashboard** → **Postgres Service** → **Variables**
2. **Copy `DATABASE_URL`** (not DATABASE_PUBLIC_URL)

### **Step 2: Find SECRET_KEY**
1. **Railway Dashboard** → **Your PC Service** → **Variables**
2. **Copy `SECRET_KEY`**

### **Step 3: Set Mobile Service Variables**
1. **Railway Dashboard** → **Mobile Service** → **Variables**
2. **Add these variables:**
   ```
   SECRET_KEY=your-copied-secret-key
   DEBUG=False
   IS_MOBILE_DEPLOYMENT=True
   DATABASE_URL=your-copied-database-url
   ```

### **Step 4: Update PC Service**
1. **Railway Dashboard** → **PC Service** → **Variables**
2. **Add this variable:**
   ```
   MOBILE_SERVICE_URL=https://your-mobile-service-name.up.railway.app
   ```

## 🚨 **Important Notes**

### **Database Connection:**
- ✅ **Use DATABASE_URL** - internal connection
- ❌ **Don't use DATABASE_PUBLIC_URL** - external connection
- ✅ **Same database** for both services

### **Secret Key:**
- ✅ **Use same SECRET_KEY** for both services
- ✅ **Keep it secure** - don't share publicly
- ✅ **Copy from existing PC service**

### **Mobile Service URL:**
- ✅ **Get from Railway** after mobile service deploys
- ✅ **Format**: `https://service-name.up.railway.app`
- ✅ **Add to PC service** environment variables

## 🎯 **Quick Checklist**

- [ ] **DATABASE_URL**: Copy from Postgres service variables
- [ ] **SECRET_KEY**: Copy from PC service variables
- [ ] **DEBUG**: Set to `False`
- [ ] **IS_MOBILE_DEPLOYMENT**: Set to `True` for mobile service
- [ ] **MOBILE_SERVICE_URL**: Add to PC service after mobile deploys

## 🚀 **Ready to Configure!**

Once you have these values, you can configure both services in Railway dashboard!
