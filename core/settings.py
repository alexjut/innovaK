from pathlib import Path
import os
from dotenv import load_dotenv
from django.urls import reverse_lazy

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017') # servicio nuevo de mongo  para modulo de subgrupos'.
MONGO_DB = os.getenv('MONGO_DB', 'innovak_documentos')# servicio nuevo de mongo  para modulo de subgrupos'.


CSRF_TRUSTED_ORIGINS = [
    "https://innovacion-dev1.ngrok.io",
    "https://explorador-bd.ngrok.io",
    "https://gestion-deporte-cultura.ngrok.io",
    "https://reserva2.ngrok.io",
    "https://*.ngrok.io",
]

AUTH_USER_MODEL = 'login.Usuario'




# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9-c@vfdormq39(77%s#&1sqd@7l=xf4=&1w8^$w2zy3!)yg3xu'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.login',
    'apps.kordial',
    'apps.VitalK',
    'apps.georeferenciacion',
    'apps.kactivo',
    "apps.dashboard",
    'apps.documento',
     # Utilidades
    'widget_tweaks',
        # Dash/Channels (NECESARIO para django-plotly-dash)
    'channels',                                           # <-- añadido
    'dpd_static_support',                                 # <-- añadido (assets de componentes)
    'django_plotly_dash.apps.DjangoPlotlyDashConfig',     # <-- añadido

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
# --- ASGI/WSGI ---
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Channels: capa en memoria (no requiere Redis para desarrollo)
CHANNEL_LAYERS = {                           # <-- añadido
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

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
# --- i18n/Timezone (una sola vez, en español/Bogotá) ---

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# --- Static/Media ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'static', 'dist'),
    
]


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
# --- Defaults ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
# --- OneDrive demo (tal cual lo tenías) ---
ONEDRIVE_UPLOAD_URL = "https://graph.microsoft.com/v1.0/me/drive/root:/Documentos/archivo.txt:/content"
ONEDRIVE_TOKEN = "Bearer_Token_Aquí"  # o usa refresh token dinámico