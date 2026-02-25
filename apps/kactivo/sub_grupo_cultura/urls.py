from django.urls import path
from . import views

app_name = "sub_grupo_cultura"

urlpatterns = [
    path("", views.lista, name="lista"),              # /kactivo/subgrupo-cultura/
    path("nuevo/", views.crear, name="nuevo"),        # /kactivo/subgrupo-cultura/nuevo/
    path("<int:pk>/editar/", views.editar, name="editar"),  # /kactivo/subgrupo-cultura/5/editar/
]
