"""
Cakemallow Backend — Settings (PythonAnywhere + SQLite edition)
No Celery, no Redis, no PostgreSQL required.
Uses Python threading for async tasks.
"""
import os
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core ──────────────────────────────────────────────────────────────────────
SECRET_KEY  = config('SECRET_KEY', default='django-insecure-change-me-in-production!')
DEBUG       = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'accounts',
    'products',
    'cart',
    'orders',
    'customization',
    'reviews',
    'core',
    'payments',
    'delivery_slots',
    'coupons',
    'loyalty',
    'notifications',
    'store_locations',
    'wishlist',
    'analytics',
    'otp',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cakemallow_backend.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'cakemallow_backend.wsgi.application'

# ── Database — SQLite (works on PythonAnywhere free tier) ────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':    '60/hour',
        'user':    '1000/hour',
        'payment': '20/hour',
        'otp':     '10/hour',
        'login':   '10/minute',
        'burst':   '30/minute',
    },
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'accounts.serializers.CustomTokenObtainPairSerializer',
}

# ── CORS ──────────────────────────────────────────────────────────────────────
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS  = False
    CORS_ALLOWED_ORIGINS = config(
        'CORS_ALLOWED_ORIGINS', default='http://localhost:3000'
    ).split(',')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS     = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS     = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-razorpay-signature',
]

# ── Production security (PythonAnywhere handles HTTPS — don't redirect here) ──
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    X_FRAME_OPTIONS                = 'DENY'
    # NOTE: PythonAnywhere handles SSL termination at their proxy.
    # SECURE_SSL_REDIRECT must be False or it will cause redirect loops.
    SECURE_SSL_REDIRECT            = False
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    # HSTS only if you have a custom domain with HTTPS properly configured
    # SECURE_HSTS_SECONDS          = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD          = True

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND    = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST       = config('EMAIL_HOST', default='')
EMAIL_PORT       = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL', default='Cakemallow <noreply@cakemallow.com>')

# ── Razorpay ──────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID         = config('RAZORPAY_KEY_ID', default='rzp_test_xxx')
RAZORPAY_KEY_SECRET     = config('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')

# ── SMS — Fast2SMS ─────────────────────────────────────────────────────────────
FAST2SMS_API_KEY = config('FAST2SMS_API_KEY', default='')

# ── WhatsApp ──────────────────────────────────────────────────────────────────
WHATSAPP_PROVIDER = config('WHATSAPP_PROVIDER', default='')
GUPSHUP_API_KEY   = config('GUPSHUP_API_KEY', default='')
GUPSHUP_SOURCE    = config('GUPSHUP_SOURCE', default='')
AISENSY_API_KEY   = config('AISENSY_API_KEY', default='')

# ── FCM — Firebase Push Notifications ─────────────────────────────────────────
FCM_SERVICE_ACCOUNT_FILE = config('FCM_SERVICE_ACCOUNT_FILE', default='')
FCM_PROJECT_ID           = config('FCM_PROJECT_ID', default='')

# ── Inventory ─────────────────────────────────────────────────────────────────
LOW_STOCK_THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', 5))

# ── Admin branding ────────────────────────────────────────────────────────────
ADMIN_SITE_HEADER  = 'Cakemallow Operations'
ADMIN_SITE_TITLE   = 'Cakemallow Admin'
ADMIN_INDEX_TITLE  = 'Dashboard'

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django':        {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'payments':      {'handlers': ['console'], 'level': 'INFO',    'propagate': False},
        'notifications': {'handlers': ['console'], 'level': 'INFO',    'propagate': False},
        'orders':        {'handlers': ['console'], 'level': 'INFO',    'propagate': False},
        'products':      {'handlers': ['console'], 'level': 'INFO',    'propagate': False},
    },
}
