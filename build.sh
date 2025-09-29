#!/bin/bash
# Build script for Render deployment

# Install Python 3.12
pyenv install 3.12.4
pyenv local 3.12.4

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
