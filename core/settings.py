from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

from django.urls import reverse_lazy


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

_DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

_allowed_hosts_raw = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
if not ALLOWED_HOSTS and not _DEBUG:
    raise RuntimeError("ALLOWED_HOSTS vacío en producción. Revisa .env")

CSRF_TRUSTED_ORIGINS = [
    "https://intranet-public-alk.ngrok.app",
]



AUTH_USER_MODEL = 'login.Usuario'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SHOW_SCHEMA_HINTS = False
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definida en el entorno. Revisa .env")

# SECURITY WARNING: don't run with debug turned on in producción!
DEBUG = _DEBUG  # M13: lectura única de os.environ arriba




# Application definition

INSTALLED_APPS = [
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.login',
    'apps.georeferenciacion',
    'apps.kactivo',
    "apps.dashboard",
    'apps.presupuesto',
    "apps.votaciones",
    'widget_tweaks',
    'django.contrib.humanize',
]

LOGIN_URL = reverse_lazy('login:login')
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

BASE_DIR = Path(__file__).resolve().parent.parent
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

TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "apps.login.context_processors.theme_context",
    "apps.dashboard.context_processors.breadcrumbs",
    "apps.dashboard.context_processors.static_version",
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases



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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'static', 'dist'),
    os.path.join(BASE_DIR, 'static', 'mapas'), 
]


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Cache (Redis) ────────────────────────────────────────────────
# Redis ya está corriendo en el container 'redis' (alias en network compose).
# REDIS_URL viene de docker-compose.yml: 'redis://redis:6379/0'.
# Usamos /1 para cache (separado de /0 que queda para channels/sesiones futuras).
_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_CACHE_URL = _REDIS_URL.rsplit("/", 1)[0] + "/1"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": _CACHE_URL,
        "TIMEOUT": 300,  # 5 min default
        "KEY_PREFIX": "innovak",
    }
}

# Sesiones en Redis puro — TTL automático del cookie, sin escritura
# duplicada a BD (cached_db escribía en ambos lados). Redis ya tiene
# volume persistente en docker-compose.yml.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

ONEDRIVE_UPLOAD_URL = "https://graph.microsoft.com/v1.0/me/drive/root:/Documentos/archivo.txt:/content"
ONEDRIVE_TOKEN = os.environ.get("ONEDRIVE_TOKEN", "")