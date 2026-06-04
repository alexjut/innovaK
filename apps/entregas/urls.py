"""URLs del módulo Entregas de insumos / utensilios."""
from django.urls import path

from apps.entregas import views
from apps.entregas.api.public import (
    CatalogosPublicView,
    InscribirPublicView,
)
from apps.entregas.api.views import (
    EntregaDetailView,
    EntregaEstadoView,
    EntregaListView,
)

app_name = "entregas"

urlpatterns = [
    # ── API REST pública (AllowAny) — wizard Angular ─────────────
    path(
        "api/publico/<int:evento_id>/catalogos/",
        CatalogosPublicView.as_view(),
        name="api_publico_catalogos",
    ),
    path(
        "api/publico/<int:evento_id>/inscribir/",
        InscribirPublicView.as_view(),
        name="api_publico_inscribir",
    ),

    # ── Organizador (HTML) ───────────────────────────────────────
    path("entregas/",                   views.entregas_list,    name="entregas_list"),
    path("entregas/<int:pk>/",          views.entrega_detalle,  name="entrega_detalle"),
    path("entregas/<int:pk>/validar/",  views.entrega_validar,  name="entrega_validar"),
    path("entregas/<int:pk>/rechazar/", views.entrega_rechazar, name="entrega_rechazar"),

    # ── API REST DRF organizador ─────────────────────────────────
    path("api/entregas/",                 EntregaListView.as_view(),   name="api_entregas_list"),
    path("api/entregas/<int:pk>/",        EntregaDetailView.as_view(), name="api_entrega_detalle"),
    path("api/entregas/<int:pk>/estado/", EntregaEstadoView.as_view(), name="api_entrega_estado"),
]
