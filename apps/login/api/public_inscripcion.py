"""APIView DRF PÚBLICA — catálogos para el form de inscripción genérica.

Espeja `apps.entregas.api.public.CatalogosPublicView`. Sirve los catálogos
del form público de inscripción de participante (el flujo por defecto de un
evento sin tipo específico) que consume el componente Angular
`/app/p/inscripcion/:id`.

    GET /api/eventos/<evento_id>/inscripcion/catalogos/
        → catálogos para los dropdowns + metadatos del evento.

El POST de creación lo maneja el endpoint ya existente
`InscripcionEventoCreateView` (`POST /api/eventos/<id>/inscripciones/`).

Auth: AllowAny (el participante lo llena por QR sin login). Si el evento
está cerrado NO devuelve 410: incluye `evento.abierto = false` para que el
front muestre la pantalla cerrada (mismo contrato que entregas).
"""
from datetime import date

from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.models import Evento


def _catalogo(tabla: str) -> list[dict]:
    """Lee {codigo, nombre} de un catálogo y lo devuelve como {value, label}."""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT codigo, nombre FROM {tabla} ORDER BY nombre")
        return [{"value": c, "label": n} for c, n in cursor.fetchall()]


def _evento_abierto(evento: Evento) -> bool:
    """True si el evento acepta inscripciones (activo y dentro de fecha_fin)."""
    if not evento.activo:
        return False
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return False
    return True


class CatalogosInscripcionPublicView(APIView):
    """GET catálogos para el form público de inscripción de participante.

    URL: /api/eventos/<evento_id>/inscripcion/catalogos/

    Público (AllowAny). Si el evento no existe → 404. Si está cerrado NO
    devuelve 410: incluye `evento.abierto = false`. Catálogos como listas
    planas {value, label}.
    """
    permission_classes = [AllowAny]

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        return Response({
            "evento": {
                "id": evento.id,
                "nombre": evento.nombre or "(sin nombre)",
                "fecha_fin": evento.fecha_fin,
                "abierto": _evento_abierto(evento),
            },
            "sexos": _catalogo("sexo"),
            "generos": _catalogo("identidad_genero"),
            "orientaciones": _catalogo("orientacion_sexual"),
            "grupos_etnicos": _catalogo("grupo_etnico"),
            "upz": _catalogo("upz"),
            "barrios": _catalogo("barrio"),
        })
