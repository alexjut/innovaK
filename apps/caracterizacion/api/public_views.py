"""API pública DRF de caracterización (AllowAny) — wizards Angular-ready.

Dos endpoints genéricos schema-driven que sirven los 6 sectores con
UN solo wizard dinámico en Angular:

    GET  /caracterizacion/api/publico/<evento_id>/schema/
         → introspecta el Django Form del sector del evento y devuelve
           un esquema JSON de campos. Override `?sector=<codigo>` para
           construir el schema sin evento (testing / preview).

    POST /caracterizacion/api/publico/<evento_id>/
         → instancia el Form del sector con request.data + request.FILES,
           valida y guarda reusando la misma cadena Persona→Beneficiario
           →Caracterización de las views HTML. multipart para firma salud.

Sin login (AllowAny): el ciudadano los llena escaneando el QR del evento.
Las views HTML legacy (`views/<sector>.py`) siguen intactas y vivas.
"""
from __future__ import annotations

from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from apps.login.api.qr_token import QrTokenPermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.caracterizacion.forms.cultura import CulturaForm
from apps.caracterizacion.forms.deporte import DeporteForm
from apps.caracterizacion.forms.mujer import MujerForm
from apps.caracterizacion.forms.participacion_ciudadana import ParticipacionCiudadanaForm
from apps.caracterizacion.forms.poblacional import PoblacionalForm
from apps.caracterizacion.forms.salud import SaludForm
from apps.caracterizacion.sectores import (
    SECTOR_CULTURA,
    SECTOR_DEPORTE,
    SECTOR_MUJER,
    SECTOR_PARTICIPACION,
    SECTOR_POBLACIONAL,
    SECTOR_SALUD,
    SECTORES_LABEL,
    SECTORES_VALIDOS,
)
from apps.login.models.evento import Evento

from . import public_save
from .schema_introspect import schema_de_form


# Registro único: sector → (FormClass, save_callable).
# Mantiene en un solo sitio el binding form/guardado de cada wizard.
_REGISTRO = {
    SECTOR_CULTURA:       (CulturaForm,                 public_save.guardar_cultura),
    SECTOR_DEPORTE:       (DeporteForm,                 public_save.guardar_deporte),
    SECTOR_MUJER:         (MujerForm,                   public_save.guardar_mujer),
    SECTOR_SALUD:         (SaludForm,                   public_save.guardar_salud),
    SECTOR_POBLACIONAL:   (PoblacionalForm,             public_save.guardar_poblacional),
    SECTOR_PARTICIPACION: (ParticipacionCiudadanaForm,  public_save.guardar_participacion),
}


def _cargar_evento_abierto(evento_id):
    """Devuelve (evento, None) si el evento existe y acepta caracterización,
    o (None, Response) con el error correspondiente (404/400)."""
    evento = (
        Evento.objects
        .select_related("tipo_evento")
        .filter(pk=evento_id)
        .first()
    )
    if evento is None:
        return None, Response({"detail": "El evento no existe."}, status=404)
    if (not evento.activo or not evento.tipo_evento
            or not evento.tipo_evento.permite_caracterizacion):
        return None, Response(
            {"detail": "Este evento no acepta caracterización pública."},
            status=400,
        )
    return evento, None


def _sector_de(evento) -> str | None:
    return (evento.sector_caracterizacion or "").strip().lower() or None


class CaracterizacionPublicSchemaView(APIView):
    """GET schema del wizard del sector (AllowAny)."""

    permission_classes = [QrTokenPermission]

    def get(self, request, evento_id):
        # Override de testing/preview: ?sector=<codigo> arma el schema sin
        # depender del sector real del evento (hoy hay 0 eventos reales).
        override = (request.query_params.get("sector") or "").strip().lower() or None

        evento = (
            Evento.objects.filter(pk=evento_id)
            .only("id", "nombre", "sector_caracterizacion")
            .first()
        )

        if override:
            sector = override
            evento_info = (
                {"id": evento.id, "nombre": evento.nombre} if evento else
                {"id": evento_id, "nombre": None}
            )
        else:
            if evento is None:
                return Response({"detail": "El evento no existe."}, status=404)
            sector = _sector_de(evento)
            evento_info = {"id": evento.id, "nombre": evento.nombre}

        if not sector or sector not in SECTORES_VALIDOS:
            return Response(
                {"detail": f"Sector '{sector}' inválido o no definido para el evento."},
                status=400,
            )
        if sector not in _REGISTRO:
            return Response(
                {"detail": f"Sector '{sector}' aún no implementado."},
                status=400,
            )

        form_cls, _ = _REGISTRO[sector]
        form = form_cls()
        return Response({
            "sector": sector,
            "sector_label": SECTORES_LABEL.get(sector, sector),
            "evento": evento_info,
            "fields": schema_de_form(form),
        })


class CaracterizacionPublicSubmitView(APIView):
    """POST captura del wizard del sector (AllowAny, multipart para firma)."""

    permission_classes = [QrTokenPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, evento_id):
        evento, err = _cargar_evento_abierto(evento_id)
        if err is not None:
            return err

        sector = _sector_de(evento)
        if not sector or sector not in SECTORES_VALIDOS:
            return Response(
                {"detail": f"Sector '{sector}' inválido o no definido para el evento."},
                status=400,
            )
        if sector not in _REGISTRO:
            return Response(
                {"detail": f"Sector '{sector}' aún no implementado."},
                status=400,
            )

        form_cls, guardar = _REGISTRO[sector]
        form = form_cls(request.data, request.FILES)
        if not form.is_valid():
            return Response(
                {"detail": "Hay errores en el formulario.",
                 "errors": form.errors},
                status=400,
            )

        try:
            nuevo_id = guardar(form.cleaned_data, evento.id, request)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Error guardando caracterización sector=%s evento=%s", sector, evento.id
            )
            return Response(
                {"detail": "Ocurrió un error al guardar tu información. Intenta de nuevo."},
                status=400,
            )

        return Response(
            {"id": nuevo_id,
             "detail": f"Caracterización de {SECTORES_LABEL.get(sector, sector)} registrada."},
            status=201,
        )
