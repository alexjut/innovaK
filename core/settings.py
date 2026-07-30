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
    'jazzmin',                # tema moderno del admin (debe ir ANTES de django.contrib.admin)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.login',
    'apps.georeferenciacion',
    "apps.dashboard",
    'apps.presupuesto',
    "apps.votaciones",
    'apps.banco_iniciativas',
    'apps.caracterizacion',
    'apps.jovenes_a_la_e',
    'apps.entregas',
    'apps.festivales',
    'apps.documentos',
    'apps.onboarding',
    'widget_tweaks',
    'django.contrib.humanize',
    # Etapa B Plan Frontend — API REST con DRF (regla Angular-ready).
    'rest_framework',
    # Etapa C Plan Frontend #1 — OpenAPI 3 autogenerado para Angular
    'drf_spectacular',
    # Etapa D Plan Frontend PR-5 — CORS para que Angular dev (:4200) consuma /api/*
    'corsheaders',
]

# ─────────────────────────────────────────────────────────────────────
# Django REST Framework — Etapa B Plan Frontend
# ─────────────────────────────────────────────────────────────────────
# Coexistencia de dos esquemas de autenticación:
#   * SessionAuthentication: usuarios logueados con cookies (templates Django).
#     Sigue siendo el modo principal para el sidebar / hubs / formularios.
#   * JWTAuthentication: clientes externos (Angular futuro, móvil, scripts).
#     Tokens cortos (15 min access) + refresh (7 días).
#
# El orden importa: SessionAuth primero porque un browser ya logueado no
# necesita token. JWT solo se evalúa si la sesión no autentica.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # JWT PRIMERO: el SPA Angular manda Bearer. Si SessionAuthentication
        # va primero y existe cookie de sesión (la crea MeView), DRF autentica
        # por sesión y EXIGE CSRF en POST/PATCH → 403. Con JWT primero, el
        # Bearer autentica sin CSRF; sin Bearer cae a sesión normal.
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # BrowsableAPIRenderer solo en DEBUG — útil para inspeccionar endpoints en /api/
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # Etapa C Plan Frontend #1 — OpenAPI 3 (drf-spectacular)
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ─────────────────────────────────────────────────────────────────────
# drf-spectacular — OpenAPI 3 + Swagger UI (Etapa C #1)
# ─────────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'innovaK API',
    'DESCRIPTION': (
        'API REST del sistema de información interno de la Alcaldía Local '
        'de Kennedy (innovaK). Contratos JSON estables Angular-ready para '
        'los módulos productivos: Banco de Iniciativas, Jóvenes a la E, '
        'Caracterización ciudadana, Presupuesto, Eventos/Cursos, Votaciones '
        'y Dashboard de KPIs.\n\n'
        'Autenticación: SessionAuth (cookies, browser) o JWT (Bearer token). '
        'Algunos endpoints son AllowAny (formularios públicos vía QR).'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Autenticación', 'description': 'JWT (obtener, refrescar, verificar token).'},
        {'name': 'Banco de Iniciativas', 'description': 'Inscripción pública + organizador.'},
        {'name': 'Jóvenes a la E', 'description': 'Entrega de becas (convenios 773-2025 y 955-2025).'},
        {'name': 'Caracterización', 'description': '6 sectores: cultura, deporte, mujer, salud, poblacional, participación.'},
        {'name': 'Presupuesto', 'description': 'Proyectos, contratos, metas, KPIs, avances.'},
        {'name': 'Eventos', 'description': 'Inscripción pública + cursos (sesiones, asistencia, notas, reporte).'},
        {'name': 'Votaciones', 'description': 'Eventos de votación, candidatos, resultados.'},
        {'name': 'Dashboard', 'description': 'KPIs presupuestales agregados.'},
        {'name': 'Georreferenciación', 'description': 'Lugares + conteos del mapa de Kennedy.'},
    ],
    'CONTACT': {'name': 'Alcaldía Local de Kennedy'},
    'LICENSE': {'name': 'Uso interno'},
}

# ─────────────────────────────────────────────────────────────────────
# JWT (simplejwt) — Etapa B Plan Frontend tarea #10
# ─────────────────────────────────────────────────────────────────────
from datetime import timedelta as _timedelta  # noqa: E402

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': _timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': _timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,         # un refresh = un token; cliente debe pedir uno nuevo al expirar.
    'BLACKLIST_AFTER_ROTATION': False,       # sin DB de blacklist (la activamos cuando llegue cliente real).
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,               # reusa SECRET_KEY de Django (.env). Cuando llegue cliente
                                              # real, considerar rotar SECRET_KEY o agregar JWT_SIGNING_KEY propia.
    'AUTH_HEADER_TYPES': ('Bearer',),        # Authorization: Bearer <token>
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

LOGIN_URL = reverse_lazy('login:login')
MIDDLEWARE = [
    # Etapa D PR-5: CORS middleware DEBE ir antes de CommonMiddleware
    # para que las cabeceras se agreguen en respuestas API.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Etapa D PR-13.5: SPA Angular sirve bajo /app/* y embebe páginas
# Django (mapa Leaflet, hub Actividades) en iframes del MISMO origen.
# Django 4.2 default = 'DENY'; lo abrimos al mismo origen.
X_FRAME_OPTIONS = "SAMEORIGIN"

# ─────────────────────────────────────────────────────────────────────
# CORS — Etapa D PR-5 Plan Frontend
# ─────────────────────────────────────────────────────────────────────
# Angular dev server corre en :4200 y necesita llamar al backend Django
# (:8034). Solo allow-list explícito en DEBUG; en producción, el frontend
# vive en el mismo dominio (Nginx routing) y no hay CORS.
CORS_ALLOWED_ORIGINS = [
    'http://localhost:4200',
    'http://127.0.0.1:4200',
    # Servidor remoto innovaK (cuando el navegador está en otra máquina)
    'http://10.100.102.12:4200',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
    'x-csrftoken',
    'x-requested-with',
    'accept',
]
# Permitir el header Authorization desde el browser (necesario para JWT
# en dev cross-origin).
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

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
    "apps.login.context_processors.modulos_usuario",
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

# ─── MongoDB (storage cifrado de documentos / firmas) ─────────────
# Servicio docker-compose 'innova_mongo' corriendo en la network interna.
MONGO_HOST = os.environ.get("MONGO_HOST", "innova_mongo")
MONGO_PORT = int(os.environ.get("MONGO_PORT", "27017"))
MONGO_USER = os.environ.get("MONGO_USER", "")
MONGO_PASS = os.environ.get("MONGO_PASS", "")
MONGO_DB = os.environ.get("MONGO_DB", "innova_documentos")

# Clave AES-256 (32 bytes en base64). Generar con:
#   python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
DOCUMENTOS_AES_KEY = os.environ.get("DOCUMENTOS_AES_KEY", "")

# Tamaño máximo de upload (firmas + soportes). 2 MB por defecto.
DOCUMENTOS_MAX_UPLOAD_BYTES = int(os.environ.get("DOCUMENTOS_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))


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

# ─── Hardening QR públicos (decisión #6, fase 1) ─────────────────
# Los QR llevan ?t=<HMAC> y QrTokenPermission lo valida en modo suave
# (solo log). Fase 2: exportar QR_TOKEN_ENFORCE=true en .env y reiniciar
# para bloquear (403) los accesos sin token válido.
QR_TOKEN_ENFORCE = os.environ.get("QR_TOKEN_ENFORCE", "False").lower() == "true"

# ─── Hardening TLS (PR-J3) ───────────────────────────────────────
# Activación condicional: cuando esté la puerta gov.net abierta y nginx
# tenga certificado, exportar BEHIND_TLS=true en .env y reiniciar.
# Nada de esto rompe en HTTP plano; solo se enciende si el env lo dice.
_BEHIND_TLS = os.environ.get("BEHIND_TLS", "False").lower() == "true"
if _BEHIND_TLS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31_536_000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ─── Logger estructurado (M11) ───────────────────────────────────
# Formato key=value plano (parseable por Loki/journald, legible humano).
# Nivel por env var DJANGO_LOG_LEVEL (default INFO en prod, DEBUG si DEBUG=true).
_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "kv": {
            "format": (
                'ts="%(asctime)s" level=%(levelname)s logger=%(name)s '
                'pid=%(process)d msg=%(message)s'
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
        "simple": {"format": "%(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "kv",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django":      {"handlers": ["console"], "level": "INFO",  "propagate": False},
        "django.db":   {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Apps innovaK — un solo prefijo para filtrar fácil
        "apps":        {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False},
        "core":        {"handlers": ["console"], "level": _LOG_LEVEL, "propagate": False},
    },
}

# ─── OneDrive / Microsoft Graph ──────────────────────────────────
# Espejo LEGIBLE de los soportes del Banco de Iniciativas
# (apps/documentos/services/onedrive_storage.py). Mongo sigue siendo el
# sistema de registro y el que cifra; OneDrive es la copia que el área de
# Deportes lee sin entrar al aplicativo.
#
# Autenticación app-only (client credentials). Las credenciales van SOLO
# en .env — este repo es PÚBLICO, nunca se escriben aquí ni en docs.
# Si alguna falta, el servicio queda inactivo, lo dice en el log y la
# radicación sigue funcionando normalmente.
#
# Variables esperadas en .env:
#   ONEDRIVE_TENANT_ID       GUID del tenant de Entra ID
#   ONEDRIVE_CLIENT_ID       GUID de la app registrada
#   ONEDRIVE_CLIENT_SECRET   secreto de la app (rotable)
#   ONEDRIVE_DRIVE_ID        id del drive destino (no se usa /me/drive:
#                            app-only no tiene usuario interactivo)
#   ONEDRIVE_CARPETA_RAIZ    carpeta contenedora (default más abajo)
ONEDRIVE_TENANT_ID = os.environ.get("ONEDRIVE_TENANT_ID", "")
ONEDRIVE_CLIENT_ID = os.environ.get("ONEDRIVE_CLIENT_ID", "")
ONEDRIVE_CLIENT_SECRET = os.environ.get("ONEDRIVE_CLIENT_SECRET", "")
ONEDRIVE_DRIVE_ID = os.environ.get("ONEDRIVE_DRIVE_ID", "")
ONEDRIVE_CARPETA_RAIZ = os.environ.get("ONEDRIVE_CARPETA_RAIZ", "Banco de Iniciativas")

# Legacy (token delegado de un solo archivo). Sin uso en código; se
# conserva porque docs/infra lo listan. El flujo nuevo es el de arriba.
ONEDRIVE_UPLOAD_URL = "https://graph.microsoft.com/v1.0/me/drive/root:/Documentos/archivo.txt:/content"
ONEDRIVE_TOKEN = os.environ.get("ONEDRIVE_TOKEN", "")


# =====================================================================
# Jazzmin — tema moderno para Django admin (AdminLTE 3 + Bootstrap 4).
# Branding institucional Alcaldía Local de Kennedy.
# =====================================================================
JAZZMIN_SETTINGS = {
    "site_title": "innovaK Admin",
    "site_header": "innovaK · Alcaldía Local Kennedy",
    "site_brand": "innovaK",
    "welcome_sign": "Sistema de información — Alcaldía Local de Kennedy",
    "copyright": "Alcaldía Local de Kennedy",
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Inicio", "url": "/dashboard/", "permissions": ["auth.view_user"]},
        {"name": "Volver al sistema", "url": "/dashboard/", "new_window": False},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": ["auth", "login", "presupuesto", "georeferenciacion",
                              "votaciones", "banco_iniciativas",
                              "caracterizacion", "dashboard"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "login": "fas fa-id-card",
        "presupuesto": "fas fa-coins",
        "georeferenciacion": "fas fa-map-marked-alt",
        "votaciones": "fas fa-vote-yea",
        "banco_iniciativas": "fas fa-lightbulb",
        "caracterizacion": "fas fa-clipboard-list",
        "dashboard": "fas fa-chart-line",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "default",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-danger navbar-dark",   # rojo institucional Alcaldía
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-danger",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "brand_small_text": False,
    "brand_colour": "navbar-danger",
    "accent": "accent-danger",
    "actions_sticky_top": True,
}