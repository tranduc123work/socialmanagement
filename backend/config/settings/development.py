"""
Development settings
"""
from .base import *

DEBUG = True

INSTALLED_APPS += [
    'django_extensions',
]

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
