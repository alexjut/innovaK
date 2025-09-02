from django.urls import path
from .views.catalogo import ping, proyectos_list, proyecto_nuevo, proyecto_editar, actividad_nueva, contrato_nuevo, home
from .views.api import api_subgrupos_por_dependencia, api_crear_subgrupo

app_name = "presupuesto"
urlpatterns = [
    path("ping/", ping, name="ping"),
    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/nuevo/", proyecto_nuevo, name="proyecto_nuevo"),
    path("proyectos/<int:pk>/editar/", proyecto_editar, name="proyecto_editar"),
    path("actividades/nueva/", actividad_nueva, name="actividad_nueva"),
    path("contratos/nuevo/", contrato_nuevo, name="contrato_nuevo"),
    path("home/", home, name="home"),

    #apis
    path("api/subgrupos/", api_subgrupos_por_dependencia, name="api_subgrupos"),
    path("api/subgrupos/create/", api_crear_subgrupo, name="api_subgrupos_create"),
]