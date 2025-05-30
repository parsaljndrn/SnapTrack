# production_settings.py
import os
from .settings import *

# Security Settings
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = [
    'snaptrack-0scd.onrender.com',  # Your actual Render URL
    'localhost',
    '127.0.0.1'
]

# Database Configuration
# Render's SQLite handling requires special consideration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/opt/render/project/src/db.sqlite3',
    }
}

# Static Files Configuration for Production
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media Files Configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security Enhancements
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [
    'https://snaptrack-0scd.onrender.com',
]

# QR Code Settings - Use environment variable
QR_ENCRYPTION_KEY = os.environ.get('QR_ENCRYPTION_KEY', 'K8-7wJxlLRmn4lKm-yFX3_8tJhCQcvJgkY8wFqP7-A8=')

# Production-specific middleware that includes WhiteNoise
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]