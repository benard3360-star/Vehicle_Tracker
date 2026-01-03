"""
Production settings for Azure deployment
"""
import os
from .settings import *
import environ

env = environ.Env()

# Security
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-production-secret-key')
ALLOWED_HOSTS = [
    'your-app-name.azurewebsites.net',
    'localhost',
    '127.0.0.1'
]

# Database - Azure PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Static files with WhiteNoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database optimization settings
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS']['MAX_CONNS'] = 20

# Cache configuration for faster data loading
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'