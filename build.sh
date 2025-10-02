#!/bin/bash
# Build script for Railway deployment

echo "=== BUILD PHASE ==="
echo "Python version: $(python --version)"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Note: We do NOT run migrations or collectstatic here
# These will be done in start.sh when the app starts
echo "Build phase complete. Migrations and static files will be handled at runtime."
