from django.urls import path

from apps.caracterizacion.views.public import (
    caracterizacion_publica,
    api_persona_por_doc,
)

app_name = "caracterizacion"

urlpatterns = [
    path("api/persona/", api_persona_por_doc, name="api_persona_por_doc"),
    path("<int:evento_id>/", caracterizacion_publica, name="publica"),
]
