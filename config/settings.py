# Import library configurations
from config.libraries.rest_framework import REST_FRAMEWORK
from config.libraries.jwt import SIMPLE_JWT
from config.libraries.cors import CSRF_TRUSTED_ORIGINS, CORS_ALLOWED_ORIGINS, CORS_ALLOW_ALL_ORIGINS, CORS_ORIGIN_ALLOW_ALL, CORS_ALLOW_CREDENTIALS, CORS_ORIGIN_WHITELIST

# CORS va CSRF sozlamalari
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_ALL_ORIGINS = CORS_ALLOW_ALL_ORIGINS
CORS_ORIGIN_ALLOW_ALL = CORS_ORIGIN_ALLOW_ALL
CORS_ALLOW_CREDENTIALS = CORS_ALLOW_CREDENTIALS
CORS_ORIGIN_WHITELIST = CORS_ORIGIN_WHITELIST

# CORS qo'shimcha sozlamalar
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
from config.libraries.email import EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
from config.libraries.cache import CACHES
from config.libraries.swagger import SWAGGER_SETTINGS, SWAGGER_UI_OAUTH2_CONFIG

import os
import warnings
from datetime import timedelta
from pathlib import Path

# Suppress pkg_resources deprecation warnings
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    load_dotenv = None


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*jp&pl1ye6t5h$5#0lx$%3j=j7h@_*###3vyw!hn=2i%g%y5w3'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

LOCAL_APPS = [
    'apps.v1.accounts',
    'apps.v1.website',
    'apps.v1.notification',
    'apps.v1.products',
    'apps.v1.user_objects',
    'apps.v1.documents',
    'apps.v1.orders',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
    'django_filters',
    'import_export',
    *LOCAL_APPS,
]

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    *THIRD_PARTY_APPS,
    'django_celery_beat',
]

LOCAL_MIDDLEWARE = [
    'config.middleware.middleware.JsonErrorResponseMiddleware',
    'config.middleware.middleware.Custom404Middleware',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    *LOCAL_MIDDLEWARE,
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'config.asgi.application'

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST'),
#         'PORT': os.getenv('DB_PORT'),
#     }
# }



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "/var/www/media/")

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_TIMEZONE = TIME_ZONE

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'notify-expiring-services-daily-08-00': {
        'task': 'apps.v1.notification.views.notify_expiring_services',
        'schedule': crontab(minute=0, hour=8),
    },
}

# Channel Layers - InMemoryChannelLayer faqat bir process ichida ishlaydi
# Agar Gunicorn va Daphne alohida processlarda ishlasa, Redis kerak
# Lekin agar bitta processda (Daphne) ishlatsangiz, InMemoryChannelLayer yetarli
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    },
}

ASGI_APPLICATION = 'config.asgi.application'

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'TEMPLATE': 'drf_yasg/swagger-ui.html',
}

# HTTPS uchun sozlamalar
USE_TLS = True  # Production uchun HTTPS ishlatiladi
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Nginx orqali HTTPS

BASE_URL = os.getenv('BASE_URL', '').strip()
if not BASE_URL:
    if DEBUG:
        BASE_URL = 'http://127.0.0.1:8000'  # Local development (default port 8000)
    else:
        BASE_URL = 'https://api.safecode.flowersoptrf.ru'  # Production default

if BASE_URL and not BASE_URL.startswith(('http://', 'https://')):
    BASE_URL = f'http://{BASE_URL}'