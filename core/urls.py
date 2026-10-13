from django.urls import path, include, re_path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

# Etapa D PR-5 alternativa: SPA Angular servida desde Django.
from apps.login.api.ping import PingView
from apps.login.views.spa import angular_spa

# JWT — Etapa B Plan Frontend #10. Endpoints públicos para clientes
# externos (Angular futuro, móvil, scripts). Coexisten con SessionAuth.
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# OpenAPI 3 (drf-spectacular) — Etapa C Plan Frontend #1
from rest_framework.permissions import AllowAny
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── JWT API auth ─────────────────────────────────────────────────
    # POST /api/token/         {username, password} → {access, refresh}
    # POST /api/token/refresh/ {refresh}            → {access}
    # POST /api/token/verify/  {token}              → 200/401
    path('api/token/',         TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(),    name='token_refresh'),
    path('api/token/verify/',  TokenVerifyView.as_view(),     name='token_verify'),

    # ── Vida del backend ─────────────────────────────────────────────
    # Público y mudo. Reemplaza a `/api/schema/` como prueba de conexión del
    # SPA: preguntar «¿estás vivo?» no puede exigir publicar el mapa de la API.
    path('api/ping/', PingView.as_view(), name='api_ping'),

    # ── OpenAPI 3 / Swagger / ReDoc (Etapa C #1) ─────────────────────
    # /api/schema/         → openapi.yaml (machine-readable)
    # /api/docs/           → Swagger UI (interactivo, try-it-out)
    # /api/redoc/          → ReDoc (lectura formal)
    #
    # CERRADOS a usuarios autenticados desde el 2026-09-14. Estaban sirviendo
    # 200 a cualquiera: `SPECTACULAR_SETTINGS` no definía `SERVE_PERMISSIONS`
    # y su default es AllowAny, así que las 259 rutas internas —con sus
    # parámetros y sus serializers— eran públicas. El túnel de ngrok apunta
    # directo a Django (`ngrok http 127.0.0.1:8034`), o sea que no había un
    # nginx delante filtrando nada.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',  SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    # El esquema de la API PÚBLICA, y solo de ella. Sin credenciales, porque
    # un tercero que va a generar su cliente no tiene ninguna: hoy la única
    # forma de saber qué campos devuelve es leer la ficha de conexión a mano.
    #
    # No reusa `/api/schema/` con exclusiones: apunta a un urlconf que SOLO
    # contiene la API abierta (`apps/publico/urls_esquema.py`), así que una ruta
    # interna nueva no puede colarse por olvido.
    path('api/publica/v1/esquema/',
         SpectacularAPIView.as_view(
             urlconf='apps.publico.urls_esquema',
             permission_classes=[AllowAny],
             authentication_classes=[],
             custom_settings={
                 'TITLE': 'API de Contratación Pública — Alcaldía Local de Kennedy',
                 'DESCRIPTION': (
                     'Datos abiertos de la contratación de la Alcaldía Local de '
                     'Kennedy, para consumir igual que innovaK consume SECOP II '
                     'de datos.gov.co.\n\n'
                     'Sin credenciales y solo lectura, con cupo por IP. Tres '
                     'reglas que gobiernan cada campo: ningún dato personal de '
                     'persona natural sale sin decisión escrita; `null` nunca es '
                     '`0` y cada uno viaja con su motivo; ninguna cifra sin su '
                     'corte, que se declara en `/metadatos/`.\n\n'
                     'La compatibilidad de la v1 está publicada en '
                     '`/metadatos/` → `compatibilidad`: no se quitan ni se '
                     'renombran campos, y los nuevos se agregan sin tocar los '
                     'existentes.'
                 ),
                 'VERSION': 'v1',
                 'SERVERS': [{'url': '/'}],
                 'LICENSE': {'name': 'CC-BY-4.0',
                             'url': 'https://creativecommons.org/licenses/by/4.0/'},
                 'TAGS': [{'name': 'Datos abiertos',
                           'description': 'Contratación de Kennedy desde SECOP II.'}],
             }),
         name='esquema_publico'),
    path('api/publica/v1/docs/',
         SpectacularSwaggerView.as_view(
             url_name='esquema_publico',
             permission_classes=[AllowAny],
             authentication_classes=[]),
         name='docs_publico'),

    # ── API PÚBLICA de datos abiertos ────────────────────────────────
    # Solo lectura, sin credenciales y con cupo por IP. Es la ÚNICA superficie
    # del sistema pensada para que la lea cualquiera: ver apps/publico/README.md
    # antes de agregarle un campo.
    path('api/publica/v1/', include('apps.publico.urls', namespace='publico')),

    # API INTERNA: entrega datos personales bajo token + lista de IP, y deja
    # rastro de cada consulta. Prefijo aparte del público a propósito.
    path('api/interna/v1/', include('apps.publico.urls_interna', namespace='interna')),

    path('geo/', include('apps.georeferenciacion.urls')),
    path('', include('apps.login.urls', namespace='login')),
    path("dashboard/", include("apps.dashboard.urls")),
    path('presupuesto/', include('apps.presupuesto.urls')),
    path("votaciones/", include("apps.votaciones.urls")),
    path('banco-iniciativas/', include('apps.banco_iniciativas.urls')),
    path('caracterizacion/', include('apps.caracterizacion.urls')),
    path('jovenes-a-la-e/', include('apps.jovenes_a_la_e.urls')),
    path('entregas/', include('apps.entregas.urls')),
    path('festivales/', include('apps.festivales.urls')),
    path('educacion/', include('apps.educacion.urls')),
    path('api/onboarding/', include('apps.onboarding.urls')),

    # ── Etapa D PR-5 — Angular SPA bajo /app/* ─────────────────────────
    # Sirve el build de producción de Angular desde
    # frontend/dist/innovak-frontend/browser/. Para rebuildear:
    #   cd frontend && npm run build -- --base-href=/app/
    path('app/', angular_spa, name='angular_spa_root'),
    re_path(r'^app/(?P<resource>.*)$', angular_spa, name='angular_spa_catchall'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
