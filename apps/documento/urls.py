# apps/documento/urls.py
from django.urls import path
from .views.mongo_views import gridfs_archivos, gridfs_descargar, gridfs_eliminar

app_name = "documento"

urlpatterns = [
    path("documentos/", gridfs_archivos, name="gridfs_archivos"),
    path("documentos/<str:file_id>/descargar/", gridfs_descargar, name="gridfs_descargar"),
    path("documentos/<str:file_id>/eliminar/", gridfs_eliminar, name="gridfs_eliminar"),
]
