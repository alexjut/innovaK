"""URLs del módulo Jóvenes a la E."""
from django.urls import path

from apps.jovenes_a_la_e import views

app_name = "jovenes_a_la_e"

urlpatterns = [
    # ── Pública (sin login, vía QR) ──────────────────────────
    path("<int:evento_id>/beca/", views.entrega_beca_form,  name="form_publico_beca"),
    path("exitoso/<int:pk>/",     views.entrega_exitosa,    name="entrega_exitosa"),

    # ── Organizador ──────────────────────────────────────────
    path("entregas/",             views.entregas_list,      name="entregas_list"),
    path("entregas/<int:pk>/",    views.entrega_detalle,    name="entrega_detalle"),
    path("entregas/<int:pk>/validar/",  views.entrega_validar,  name="entrega_validar"),
    path("entregas/<int:pk>/rechazar/", views.entrega_rechazar, name="entrega_rechazar"),
]
