"""
Django settings for Clinical Trial Control Tower.

For more information on this file, see:
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see:
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from datetime import timedelta
import environ

# Initialize environment variables
env = environ.Env(
    # Set default values and casting
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

# Build paths inside the project
# BASE_DIR points to backend/ directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file from project root (one level up from backend/)
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-temporary-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',

    # Local apps - Clinical Trial Control Tower
    'apps.core',
    'apps.monitoring',
    'apps.safety',
    'apps.medical_coding',
    'apps.metrics',
    'apps.blockchain',
    'apps.ai_services',
    'apps.api',
    'apps.genai',
    'apps.predictive',
]

MIDDLEWARE = [
    # Security middleware
    'django.middleware.security.SecurityMiddleware',

    # CORS middleware (must be before CommonMiddleware)
    'corsheaders.middleware.CorsMiddleware',

    # Session middleware
    'django.contrib.sessions.middleware.SessionMiddleware',

    # Common middleware
    'django.middleware.common.CommonMiddleware',

    # CSRF protection
    'django.middleware.csrf.CsrfViewMiddleware',

    # Authentication middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Messages middleware
    'django.contrib.messages.middleware.MessageMiddleware',

    # Clickjacking protection
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR.parent / 'frontend' / 'html',  # Include frontend templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR.parent / 'frontend',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework Configuration
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}


# JWT Configuration
# https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# CORS Configuration
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True  # For development only


# Security Settings
# https://docs.djangoproject.com/en/5.0/topics/security/

if not DEBUG:
    # HTTPS/SSL settings for production
    SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE', default=True)
    CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE', default=True)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'


# Logging Configuration
# https://docs.djangoproject.com/en/5.0/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


# Application-specific settings

# Data Quality Index (DQI) Configuration
DQI_THRESHOLDS = {
    'LOW_RISK': 75,      # DQI score >= 75 = Low risk
    'MEDIUM_RISK': 50,   # DQI score >= 50 = Medium risk
    'HIGH_RISK': 25,     # DQI score >= 25 = High risk
    # Below 25 = Critical risk
}

# Clean Patient Status Configuration
CLEAN_PATIENT_TOLERANCES = {
    'MAX_MISSING_VISITS': 0,
    'MAX_MISSING_PAGES': 0,
    'MAX_OPEN_QUERIES': 0,
    'MAX_NON_CONFORMANT': 0,
    'MIN_SDV_COMPLETION': 100,  # Percentage
    'MIN_PI_SIGNATURE_COMPLETION': 100,  # Percentage
    'MAX_SAE_DISCREPANCIES': 0,
}

# Data Import Configuration
DATA_IMPORT_BATCH_SIZE = 1000
MAX_UPLOAD_SIZE = env('MAX_UPLOAD_SIZE', default=10485760)  # 10MB

# Encryption Configuration (Phase 11)
ENCRYPTION_KEY = env('ENCRYPTION_KEY', default='')
DATABASE_ENCRYPTION_KEY = env('DATABASE_ENCRYPTION_KEY', default='')

# AI Services Configuration (Phase 5)
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')

# ML Models Configuration (Phase 6)
ML_MODELS_DIR = BASE_DIR / 'ml_models'

# Blockchain Configuration (Phase 7)
BLOCKCHAIN_NETWORK = env('BLOCKCHAIN_NETWORK', default='http://127.0.0.1:8545')
BLOCKCHAIN_PRIVATE_KEY = env('BLOCKCHAIN_PRIVATE_KEY', default='')

# Celery Configuration (for async tasks)
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
