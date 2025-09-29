#!/bin/bash

# SAHA-AI Deployment Setup Script
echo "🚀 Setting up SAHA-AI for deployment..."

# Create logs directory
mkdir -p logs

# Install production requirements
echo "📦 Installing production dependencies..."
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser (if not exists)
echo "👤 Setting up admin user..."
python manage.py shell -c "
from django.contrib.auth.models import User
from users.models import UserProfile
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@saha-ai.com', 'Nithin#1906')
    print('✅ Admin user created')
else:
    print('✅ Admin user already exists')
"

# Generate invite codes
echo "🎫 Generating invite codes..."
python manage.py shell -c "
from users.models import InviteCode
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

admin_user = User.objects.get(username='admin')
# Create 10 invite codes
for i in range(10):
    InviteCode.objects.create(
        created_by=admin_user,
        expires_at=timezone.now() + timedelta(days=30),
        max_uses=5
    )
print('✅ 10 invite codes generated')
"

echo "✅ SAHA-AI deployment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in your deployment platform"
echo "2. Deploy your code"
echo "3. Access admin dashboard at /users/admin-dashboard/"
echo "4. Use invite codes to register new users"
echo ""
echo "🔑 Admin credentials:"
echo "Username: admin"
echo "Password: Nithin#1906"
