from django.urls import path

from apps.caracterizacion.views.public import caracterizacion_publica

app_name = "caracterizacion"

urlpatterns = [
    path("<int:evento_id>/", caracterizacion_publica, name="publica"),
]
