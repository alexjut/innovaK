"""URLs públicas del módulo de caracterización.

Mantenidas separadas de `apps.kactivo.urls` (que vive bajo /kactivo/)
porque la caracterización va bajo /caracterizacion/<evento_id>/ a nivel
raíz, para que el QR generado en `crear_evento` apunte a una URL corta.
"""
from django.urls import path
from .views.caracterizacion_publica import caracterizacion_placeholder

app_name = 'caracterizacion'

urlpatterns = [
    path('<int:evento_id>/', caracterizacion_placeholder, name='placeholder'),
]
