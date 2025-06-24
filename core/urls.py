from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('geo/', include('apps.georeferenciacion.urls')),  
    path('', include('apps.login.urls', namespace='login')),
    path('kactivo/', include('kactivo.urls')),
    
]


