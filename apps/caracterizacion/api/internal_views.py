"""API interna DRF de caracterización (autenticada) — wizard Angular para
funcionarios (sin QR).

Reusa EXACTAMENTE el motor schema-driven del público (`public_views._REGISTRO`,
`schema_introspect.schema_de_form`, `public_save.guardar_*`). Las únicas
diferencias del modo interno:

  - El sector llega por la URL (lo elige el funcionario), no se deriva del
    evento.
  - El evento es OPCIONAL (`evento_id` en el body); las tablas dedicadas lo
    aceptan nulo.
  - Va autenticado y gateado por el módulo `caracterizacion`; el funcionario
    logueado queda registrado (`funcionario_actual_o_none` lo resuelve desde
    `request.user`).

    GET  /caracterizacion/api/interna/<sector>/schema/
    POST /caracterizacion/api/interna/<sector>/      (multipart para firmas)
"""
from __future__ import annotations

import logging

from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.login.models.evento import Evento

from apps.caracterizacion.sectores import SECTORES_LABEL, SECTORES_VALIDOS

from .public_views import _REGISTRO
from .schema_introspect import schema_de_form

logger = logging.getLogger(__name__)

_PERMS = [ModuloRequiredPermission("caracterizacion")]


def _resolver_sector(sector):
    """Normaliza y valida el sector. None si no es válido o no implementado."""
    sector = (sector or "").strip().lower()
    if sector not in SECTORES_VALIDOS or sector not in _REGISTRO:
        return None
    return sector


class CaracterizacionInternaSchemaView(APIView):
    """GET schema del wizard interno del sector (autenticado)."""

    permission_classes = _PERMS

    def get(self, request, sector):
        sector = _resolver_sector(sector)
        if sector is None:
            return Response({"detail": "Sector inválido o no implementado."}, status=404)
        form_cls, _ = _REGISTRO[sector]
        return Response({
            "sector": sector,
            "sector_label": SECTORES_LABEL.get(sector, sector),
            "fields": schema_de_form(form_cls()),
        })


class CaracterizacionInternaSubmitView(APIView):
    """POST captura interna del sector (autenticado, multipart para firma)."""

    permission_classes = _PERMS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, sector):
        sector = _resolver_sector(sector)
        if sector is None:
            return Response({"detail": "Sector inválido o no implementado."}, status=404)

        raw = request.data.get("evento_id")
        evento_id = None
        if raw not in (None, "", "null"):
            try:
                evento_id = int(raw)
            except (TypeError, ValueError):
                return Response({"detail": "evento_id inválido."}, status=400)
            if not Evento.objects.filter(pk=evento_id).exists():
                return Response({"detail": "El evento indicado no existe."}, status=400)

        form_cls, guardar = _REGISTRO[sector]
        form = form_cls(request.data, request.FILES)
        if not form.is_valid():
            return Response(
                {"detail": "Hay errores en el formulario.", "errors": form.errors},
                status=400,
            )

        try:
            nuevo_id = guardar(form.cleaned_data, evento_id, request)
        except Exception:
            logger.exception(
                "Error guardando caracterización interna sector=%s evento=%s",
                sector, evento_id,
            )
            return Response(
                {"detail": "Ocurrió un error al guardar. Intenta de nuevo."},
                status=400,
            )

        return Response(
            {"id": nuevo_id,
             "detail": f"Caracterización de {SECTORES_LABEL.get(sector, sector)} registrada."},
            status=201,
        )
