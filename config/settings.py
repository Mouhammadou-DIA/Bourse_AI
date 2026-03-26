import os
import ssl as _ssl
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-only')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,bourse-app.onrender.com').split(',')
# On force l'ajout des domaines ngrok (même si le .env dit le contraire)
ALLOWED_HOSTS.extend(['.ngrok-free.app', '.ngrok-free.dev'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'bourse',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Pour ngrok, il faut aussi autoriser l'origine sécurisée pour les requêtes POST (ex: login)
if DEBUG:
    CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.app', 'https://*.ngrok-free.dev']


ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

ASGI_APPLICATION = 'config.asgi.application'

# ── BASE DE DONNÉES (Neon) ────────────────────────────────────────────────────
_DATABASE_URL = os.getenv('DATABASE_URL')
if _DATABASE_URL:
    import urllib.parse as _up
    _u = _up.urlparse(_DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     _u.path.lstrip('/').split('?')[0],
            'USER':     _u.username,
            'PASSWORD': _u.password,
            'HOST':     _u.hostname,
            'PORT':     str(_u.port or 5432),
            'OPTIONS':  {'sslmode': 'require'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.getenv('DB_NAME',     'bourse_db'),
            'USER':     os.getenv('DB_USER',     'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST':     os.getenv('DB_HOST',     'localhost'),
            'PORT':     os.getenv('DB_PORT',     '5432'),
        }
    }

# ── REDIS (Upstash) ───────────────────────────────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

_channel_hosts  = [REDIS_URL]
_cache_location = REDIS_URL

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG':  {'hosts': _channel_hosts},
    },
}

CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _cache_location,
        'OPTIONS': {
            'ssl_cert_reqs': None,
        } if REDIS_URL.startswith('rediss://') else {},
    }
}

CELERY_BROKER_URL     = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE       = 'Africa/Dakar'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
if REDIS_URL.startswith('rediss://'):
    CELERY_BROKER_USE_SSL        = {'ssl_cert_reqs': _ssl.CERT_NONE}
    CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': _ssl.CERT_NONE}

CELERY_BEAT_SCHEDULE = {
    'import-donnees-quotidien': {
        'task':     'bourse.tasks.import_donnees.importer_toutes_actions',
        'schedule': 60 * 60 * 24,
    },
    'calcul-indicateurs-soir': {
        'task':     'bourse.tasks.calcul_indicateurs.calculer_tous_indicateurs',
        'schedule': 60 * 60 * 6,
    },
    'check-alertes': {
        'task':     'bourse.tasks.check_alertes.verifier_alertes',
        'schedule': 60 * 5,
    },
}

# ── APIs ──────────────────────────────────────────────────────────────────────
FINNHUB_API_KEY    = os.getenv('FINNHUB_API_KEY',   '')
ALPHA_VANTAGE_KEY  = os.getenv('ALPHA_VANTAGE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN','')

# ── EMAIL ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER',     '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# ── AUTH ──────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── GENERAL ───────────────────────────────────────────────────────────────────
LANGUAGE_CODE      = 'fr-fr'
TIME_ZONE          = 'Africa/Dakar'
USE_I18N           = True
USE_TZ             = True
STATIC_URL         = '/static/'
STATICFILES_DIRS   = [BASE_DIR / 'bourse' / 'static']
STATIC_ROOT        = BASE_DIR / 'staticfiles'
MEDIA_URL          = '/media/'
MEDIA_ROOT         = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'