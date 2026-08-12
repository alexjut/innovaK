"""URLs del módulo Jóvenes a la E."""
from django.urls import path

from apps.jovenes_a_la_e import views
from apps.jovenes_a_la_e.api.public import (
    CatalogosPublicView,
    InscribirPublicView,
)
from apps.jovenes_a_la_e.api.cargues import CarguePrevalidarView
from apps.jovenes_a_la_e.api.views import (
    EntregaDetailView,
    EntregaEstadoView,
    EntregaInsightsView,
    EntregaListView,
)

app_name = "jovenes_a_la_e"

urlpatterns = [
    # ── Pública (sin login, vía QR) ──────────────────────────
    path("<int:evento_id>/beca/", views.entrega_beca_form,  name="form_publico_beca"),
    path("exitoso/<int:pk>/",     views.entrega_exitosa,    name="entrega_exitosa"),

    # ── API REST pública (AllowAny) — wizard Angular Etapa D ──
    # Coexisten con el form HTML legacy de arriba.
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

    # ── Organizador ──────────────────────────────────────────
    path("entregas/",             views.entregas_list,      name="entregas_list"),
    # Importante: rutas estáticas ANTES de la ruta con <int:pk> para que
    # no las atrape como id.
    path("entregas/insights/",    views.entregas_insights,  name="entregas_insights"),
    path("entregas/exportar/",    views.entregas_exportar_excel, name="entregas_exportar_excel"),
    path("entregas/<int:pk>/",    views.entrega_detalle,    name="entrega_detalle"),

    # ── API REST DRF (Etapa B Plan Frontend, 2026-05-27) ────────
    # Coexiste con las views HTML; consumida por clientes externos.
    path("api/insights/",                     EntregaInsightsView.as_view(), name="api_insights"),
    path("api/entregas/",                     EntregaListView.as_view(),     name="api_entregas_list"),
    path("api/entregas/<int:pk>/",            EntregaDetailView.as_view(),   name="api_entrega_detalle"),
    path("api/entregas/<int:pk>/estado/",     EntregaEstadoView.as_view(),   name="api_entrega_estado"),

    # ── Cargue masivo desde Excel ───────────────────────────────
    # Prevalidar NO escribe nada, así que sirve sin el DDL 004 aplicado.
    path("api/cargues/prevalidar/", CarguePrevalidarView.as_view(), name="api_cargue_prevalidar"),
]
