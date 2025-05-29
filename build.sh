#!/usr/bin/env bash
# build.sh - Render's build script

set -o errexit  # Exit on any error

# Install Python dependencies
pip install -r requirements.txt

# Collect static files for serving
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional)
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'your-secure-password')
    print('Superuser created successfully!')
else:
    print('Superuser already exists.')
EOF