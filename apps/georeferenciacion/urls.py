from django.urls import path
from .views.mapas import mapa_escuelas_view

urlpatterns = [
    path('mapa-escuelas/', mapa_escuelas_view, name='mapa_escuelas'),
]