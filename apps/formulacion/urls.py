"""Rutas de Formulación.

**El prefijo sigue siendo `presupuesto/`** y no es un descuido: estas rutas
nacieron dentro de esa app y las consume la pantalla del área. Mover el código a
`apps.formulacion` es un cambio de ESTRUCTURA; cambiar la URL sería un cambio de
CONTRATO, y entonces un fallo no diría cuál de los dos lo causó. Si algún día se
mueven, se mueven solas, con el frontend en el mismo movimiento.

Dos rutas cuelgan de `areas/<area>/` —el alta y el listado— para que el gate de
scope sea el mismo que el del resto de la captura del área. El resto cuelga de
la formulación: una vez creada, su área ya está en la fila y no hace falta
repetirla en la URL.
"""
from django.urls import path

from apps.formulacion.api import views as _v

app_name = "formulacion"

urlpatterns = [
    path("api/areas/<str:area>/formulaciones/",
         _v.FormulacionesAreaView.as_view(), name="api_area_formulaciones"),
    path("api/formulaciones/<int:formulacion_id>/",
         _v.FormulacionDetalleView.as_view(), name="api_formulacion_detalle"),
    path("api/formulaciones/<int:formulacion_id>/responsable/",
         _v.FormulacionResponsableView.as_view(), name="api_formulacion_responsable"),
    path("api/formulaciones/<int:formulacion_id>/estado/",
         _v.FormulacionEstadoView.as_view(), name="api_formulacion_estado"),
    path("api/formulaciones/<int:formulacion_id>/requisitos/<str:codigo>/",
         _v.FormulacionRequisitoView.as_view(), name="api_formulacion_requisito"),

    # Las observaciones son el carril de vuelta: sin ellas un «Con
    # observaciones» no dice QUÉ hay que corregir.
    path("api/formulaciones/<int:formulacion_id>/observaciones/",
         _v.FormulacionObservacionesView.as_view(),
         name="api_formulacion_observaciones"),
    path("api/formulaciones/<int:formulacion_id>/observaciones/<int:obs_id>/",
         _v.FormulacionObservacionDetalleView.as_view(),
         name="api_formulacion_observacion"),

    path("api/formulaciones/<int:formulacion_id>/documentos/",
         _v.FormulacionDocumentosView.as_view(), name="api_formulacion_documentos"),
    path("api/formulaciones/<int:formulacion_id>/documentos/<int:doc_id>/",
         _v.FormulacionDocumentoDetalleView.as_view(), name="api_formulacion_documento"),

    # El salto a contrato, en los dos sentidos: «¿en qué contrato terminé?» y
    # «¿de qué formulación nací?». Sin las dos, la traza se pierde en cuanto
    # SECOP publica.
    path("api/formulaciones/<int:formulacion_id>/contratos/",
         _v.FormulacionContratosView.as_view(), name="api_formulacion_contratos"),
    path("api/contratos/<int:contrato_id>/formulaciones/",
         _v.ContratoFormulacionesView.as_view(), name="api_contrato_formulaciones"),
]
