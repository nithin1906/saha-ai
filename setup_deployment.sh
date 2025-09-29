#!/bin/bash

# SAHA-AI Setup Script for Invite-Only Deployment
# Run this script to prepare your app for secure deployment

echo "🚀 Setting up SAHA-AI for Invite-Only Deployment..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Please activate your virtual environment first:"
    echo "   source venv/Scripts/activate  # Windows"
    echo "   source venv/bin/activate      # Mac/Linux"
    exit 1
fi

echo "✅ Virtual environment activated"

# Install new dependencies
echo "📦 Installing production dependencies..."
pip install gunicorn whitenoise psycopg2-binary redis python-decouple

# Create migrations
echo "🗄️  Creating database migrations..."
python manage.py makemigrations users

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Create admin user and invite codes
echo "👤 Creating admin user and invite codes..."
python manage.py setup_admin --username admin --email admin@saha-ai.com --password admin123 --invite-codes 10

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Test the invite system locally:"
echo "   python manage.py runserver"
echo "   Visit: http://127.0.0.1:8000/users/admin-dashboard/"
echo ""
echo "2. Create a private GitHub repository"
echo "3. Push your code to GitHub"
echo "4. Deploy to Railway/Render/Heroku"
echo "5. Configure environment variables"
echo "6. Test the production deployment"
echo ""
echo "🔐 Security Features Ready:"
echo "✅ Invite-only registration"
echo "✅ Admin approval system"
echo "✅ Access logging"
echo "✅ User management dashboard"
echo "✅ Security middleware"
echo ""
echo "📖 See DEPLOYMENT_GUIDE.md for detailed instructions"
echo ""
echo "🚀 Your SAHA-AI app is ready for secure deployment!"
