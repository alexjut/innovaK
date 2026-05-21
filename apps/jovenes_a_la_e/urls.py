"""URLs del módulo Jóvenes a la E (sólo flujo de Becas).

La dotación a sedes reusa el `tipo_evento='ENTREGA'` existente —
no requiere URL específica de este módulo.

PR-1 sólo expone placeholders para que `core/urls.py` resuelva y el smoke
test de imports pase. Las vistas reales se cablean en PR-2 (form público
de beca) y PR-3 (vista organizador + insights).
"""
from django.urls import path

from apps.jovenes_a_la_e import views

app_name = "jovenes_a_la_e"

urlpatterns = [
    # ── Pública (sin login, vía QR) ──────────────────────────
    path(
        "<int:evento_id>/beca/",
        views.entrega_beca_form,
        name="form_publico_beca",
    ),
    path(
        "exitoso/<int:pk>/",
        views.entrega_exitosa,
        name="entrega_exitosa",
    ),

    # ── Organizador (login + @modulo_required("jovenes_a_la_e")) ──
    path("entregas/",          views.entregas_list,    name="entregas_list"),
    path("entregas/<int:pk>/", views.entrega_detalle,  name="entrega_detalle"),
]
