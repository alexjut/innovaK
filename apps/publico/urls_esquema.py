"""El mapa de rutas que ve el esquema PÚBLICO. Solo la API abierta.

El filtro es estructural a propósito. El 2026-09-14 `/api/schema/` estaba
sirviendo 200 a cualquiera con las 259 rutas internas dentro —parámetros y
serializers incluidos— porque `SPECTACULAR_SETTINGS` no definía
`SERVE_PERMISSIONS` y su default es AllowAny. Se cerró.

Esto lo vuelve a abrir, pero de una forma que no puede volver a filtrarse: el
generador no recibe el urlconf del proyecto con una lista de exclusiones —que
hay que acordarse de actualizar cada vez que nace una ruta interna—, sino este,
que solo contiene la API pública. Una ruta interna nueva no aparece acá porque
no está, no porque alguien se acordó de excluirla.
"""
from django.urls import include, path

urlpatterns = [
    path("api/publica/v1/", include("apps.publico.urls", namespace="publico")),
]
