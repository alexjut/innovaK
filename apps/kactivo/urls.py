from django.urls import path
from .views import cultura, deporte

urlpatterns = [
    path('cultura/', cultura.listado_caracterizaciones, name='cultura_listado'),
    path('deporte/', deporte.listado_acudientes, name='deporte_listado'),
]
