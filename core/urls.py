from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

# JWT — Etapa B Plan Frontend #10. Endpoints públicos para clientes
# externos (Angular futuro, móvil, scripts). Coexisten con SessionAuth.
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
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

    path('geo/', include('apps.georeferenciacion.urls')),
    path('', include('apps.login.urls', namespace='login')),
    path('kactivo/', include('apps.kactivo.urls')),
    path("dashboard/", include("apps.dashboard.urls")),
    path('presupuesto/', include('apps.presupuesto.urls')),
    path("votaciones/", include("apps.votaciones.urls")),
    path('banco-iniciativas/', include('apps.banco_iniciativas.urls')),
    path('caracterizacion/', include('apps.caracterizacion.urls')),
    path('jovenes-a-la-e/', include('apps.jovenes_a_la_e.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
