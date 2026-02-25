# core/urls.py
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Apps
    path('', include(('apps.login.urls', 'login'), namespace='login')),
    path('geo/', include(('apps.georeferenciacion.urls', 'georeferenciacion'), namespace='georeferenciacion')),
    path('kactivo/', include(('apps.kactivo.urls', 'kactivo'), namespace='kactivo')),
    path('dashboard/', include(('apps.dashboard.urls', 'dashboard'), namespace='dashboard')),

    # Documentos (GridFS)
    path('', include(('apps.documento.urls', 'documento'), namespace='documento')),

    # Dash/DPD (si lo usas)
    path('django_plotly_dash/', include('django_plotly_dash.urls')),
]

# Servir estáticos/media solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=getattr(settings, "STATIC_ROOT", None))
    urlpatterns += static(settings.MEDIA_URL, document_root=getattr(settings, "MEDIA_ROOT", None))
