from django.urls import path

from apps.banco_iniciativas import views

app_name = "banco_iniciativas"

urlpatterns = [
    # ── Públicas (sin login) ────────────────────────────────────
    path(
        "<int:evento_id>/inscribir/",
        views.inscripcion_banco_form,
        name="form_publico",
    ),
    path(
        "exitoso/<int:pk>/",
        views.inscripcion_exitosa,
        name="inscripcion_exitosa",
    ),

    # ── Organizador (login requerido) ───────────────────────────
    path(
        "inscripciones/",
        views.inscripciones_list,
        name="inscripciones_list",
    ),
    path(
        "inscripciones/<int:pk>/",
        views.inscripcion_detalle,
        name="inscripcion_detalle",
    ),
    path(
        "inscripciones/<int:pk>/validar/",
        views.inscripcion_validar,
        name="inscripcion_validar",
    ),
]
