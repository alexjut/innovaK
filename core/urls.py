from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

 
urlpatterns = [
    path('admin/', admin.site.urls),
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
