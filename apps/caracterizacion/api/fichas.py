"""APIViews DRF — fichas INTERNAS de caracterización (autenticadas).

Las llena el equipo del área desde el panel autenticado (no por QR).
Reusan el motor `captura_generica` (datos en JSONB, sin DDL). El esquema
es data-driven (`services.fichas_schema`); el encabezado deriva de la
cadena del evento (`services.encabezado`).

Prefijo final: /api/caracterizacion/fichas/<sector>/...
Gating: módulo `caracterizacion`.

El sector llega en la URL. El subgrupo correspondiente se resuelve vía
`SECTORES_SUBGRUPO_ID` (cultura→1, seguridad→38). Un sector sin fichas
declaradas en `FICHAS` responde 404.
"""
import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.login.models import Evento
from apps.login.models.captura_generica import CapturaGenerica

from apps.caracterizacion.sectores import SECTORES_SUBGRUPO_ID
from apps.caracterizacion.services.catalogos_loader import cargar_catalogos
from apps.caracterizacion.services.encabezado import encabezado_de_evento
from apps.caracterizacion.services.fichas_schema import (
    FICHAS, TARGETS_VALIDOS, campos_checkbox, campos_file, ficha_de,
)
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona

logger = logging.getLogger(__name__)

_PERMS = [ModuloRequiredPermission("caracterizacion")]


def _sector_label(sector: str) -> str:
    return sector.capitalize()


def _subgrupo_de_sector(sector: str):
    """Devuelve el subgrupo_id del sector. Si el sector no tiene fichas
    declaradas en FICHAS, devuelve None (el caller responde 404)."""
    if sector not in FICHAS:
        return None
    return SECTORES_SUBGRUPO_ID.get(sector)


class FichaContextoView(APIView):
    """GET contexto/ — eventos del subgrupo seleccionables como intervención."""
    permission_classes = _PERMS

    def get(self, request, sector):
        subgrupo_id = _subgrupo_de_sector(sector)
        if subgrupo_id is None:
            return Response({"detail": "Sector no disponible."},
                            status=status.HTTP_404_NOT_FOUND)
        eventos = (
            Evento.objects
            .filter(subgrupo_id=subgrupo_id, activo=True)
            .select_related("actividad_plan")
            .order_by("-fecha_inicio", "-id")
        )
        data = []
        for ev in eventos:
            data.append({
                "id": ev.id,
                "nombre": ev.nombre or f"Evento #{ev.id}",
                "actividad_plan_id": ev.actividad_plan_id,
                "encabezado": encabezado_de_evento(ev),
            })
        return Response({"eventos": data})


class FichaSchemaView(APIView):
    """GET <target>/schema/ — esquema + catálogos de la ficha."""
    permission_classes = _PERMS

    def get(self, request, sector, target):
        if sector not in FICHAS:
            return Response({"detail": "Sector no disponible."},
                            status=status.HTTP_404_NOT_FOUND)
        if target not in TARGETS_VALIDOS:
            return Response({"detail": "Target inválido."},
                            status=status.HTTP_404_NOT_FOUND)
        esquema = ficha_de(sector, target)
        if esquema is None:
            return Response({
                "titulo": f"Ficha {target} ({_sector_label(sector)})",
                "disponible": False,
                "mensaje": "Próximamente",
            })
        return Response({
            "titulo": esquema["titulo"],
            "target": esquema["target"],
            "campos": esquema["campos"],
            "catalogos": cargar_catalogos(esquema),
        })


class FichaSubmitView(APIView):
    """POST <target>/ — crea la ficha (individuo) reusando captura_generica."""
    permission_classes = _PERMS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, sector, target):
        if sector not in FICHAS:
            return Response({"detail": "Sector no disponible."},
                            status=status.HTTP_404_NOT_FOUND)
        if target not in TARGETS_VALIDOS:
            return Response({"detail": "Target inválido."},
                            status=status.HTTP_404_NOT_FOUND)
        esquema = ficha_de(sector, target)
        if esquema is None:
            return Response({"detail": "Ficha no disponible aún."},
                            status=status.HTTP_501_NOT_IMPLEMENTED)
        subgrupo_id = _subgrupo_de_sector(sector)
        data = request.data

        evento_id = data.get("evento_id")
        if not evento_id or not str(evento_id).strip():
            return Response({"errors": {"evento_id": ["Este campo es obligatorio."]}},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            evento = Evento.objects.select_related("tipo_evento").get(pk=int(evento_id))
        except (ValueError, Evento.DoesNotExist):
            return Response({"errors": {"evento_id": ["Evento no encontrado."]}},
                            status=status.HTTP_400_BAD_REQUEST)
        if subgrupo_id is not None and evento.subgrupo_id != subgrupo_id:
            return Response(
                {"errors": {"evento_id": [f"El evento no es de {_sector_label(sector)}."]}},
                status=status.HTTP_400_BAD_REQUEST)

        checkboxes = campos_checkbox(esquema)
        files = set(campos_file(esquema))
        errores = {}
        datos = {}
        fijos = {"numero_documento": None, "nombre_legal": None}

        for campo in esquema["campos"]:
            nombre = campo["name"]
            if nombre in files:
                continue
            crudo = data.get(nombre)
            if nombre in checkboxes:
                datos[nombre] = _a_bool(crudo)
                continue
            valor = crudo.strip() if isinstance(crudo, str) else crudo
            if campo.get("required") and (valor is None or valor == ""):
                errores[nombre] = ["Este campo es obligatorio."]
                continue
            if valor not in (None, ""):
                datos[nombre] = valor
                if campo.get("map_to") in fijos:
                    fijos[campo["map_to"]] = valor

        if errores:
            return Response({"errors": errores}, status=status.HTTP_400_BAD_REQUEST)

        persona_id = None
        organizacion_id = None
        nombre_legal = fijos["nombre_legal"]

        if target == "individuo":
            nombre1 = datos.get("nombre1", "")
            apellido1 = datos.get("apellido1", "")
            try:
                persona, _ = obtener_o_crear_persona(
                    tipo_documento_codigo=_a_int(datos.get("tipo_documento")),
                    numero_documento=datos.get("numero_documento", ""),
                    nombre1=nombre1,
                    apellido1=apellido1,
                    nombre2=datos.get("nombre2"),
                    apellido2=datos.get("apellido2"),
                )
            except ValueError as e:
                return Response({"errors": {"numero_documento": [str(e)]}},
                                status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                logger.exception("Error resolviendo persona (ficha cultura individuo)")
                return Response({"detail": "No se pudo registrar la persona."},
                                status=status.HTTP_400_BAD_REQUEST)
            persona_id = persona.id
            nombre_legal = f"{nombre1} {apellido1}".strip()
        elif target == "organizacion":
            organizacion_id = self._resolver_organizacion(datos.get("nit"))

        self._subir_archivos(request, sector, target, evento, files, datos)

        try:
            captura = CapturaGenerica.objects.create(
                evento_id=evento.id,
                tipo_codigo=esquema["tipo_codigo"],
                persona_id=persona_id,
                organizacion_id=organizacion_id,
                numero_documento=fijos["numero_documento"],
                nombre_legal=nombre_legal,
                datos=datos,
                estado="enviada",
            )
        except Exception:
            logger.exception("Error guardando ficha %s %s (evento %s)", sector, target, evento.id)
            return Response({"detail": "No se pudo guardar la ficha. Intenta de nuevo."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"id": captura.id, "detail": "Ficha guardada."},
                        status=status.HTTP_201_CREATED)

    def _resolver_organizacion(self, nit):
        nit = (nit or "").strip()
        if not nit:
            return None
        try:
            from apps.login.models.contratos import Organizacion
            org = Organizacion.objects.filter(nit=nit).first()
            return org.id if org else None
        except Exception:
            logger.exception("Error resolviendo organización por nit")
            return None

    def _subir_archivos(self, request, sector, target, evento, files, datos):
        for nombre in files:
            archivo = request.FILES.get(nombre)
            if not archivo:
                continue
            try:
                from apps.documentos.services import mongo_storage
                mongo_id = mongo_storage.guardar(
                    archivo.read(),
                    archivo.content_type or "application/octet-stream",
                    owner={
                        "tipo": f"caracterizacion_{sector}_{target}",
                        "evento_id": evento.id,
                        "campo": nombre,
                    },
                )
                datos[f"{nombre}_mongo_id"] = mongo_id
            except Exception:
                logger.exception(
                    "No se pudo guardar el archivo '%s' en Mongo (evento %s)",
                    nombre, evento.id,
                )


class FichaRegistrosView(APIView):
    """GET <target>/registros/ — lista paginada de fichas del tipo."""
    permission_classes = _PERMS

    def get(self, request, sector, target):
        if sector not in FICHAS:
            return Response({"detail": "Sector no disponible."},
                            status=status.HTTP_404_NOT_FOUND)
        if target not in TARGETS_VALIDOS:
            return Response({"detail": "Target inválido."},
                            status=status.HTTP_404_NOT_FOUND)
        esquema = ficha_de(sector, target)
        if esquema is None:
            return Response({"count": 0, "page": 1, "page_size": 50, "results": []})

        qs = (
            CapturaGenerica.objects
            .select_related("evento")
            .filter(tipo_codigo=esquema["tipo_codigo"])
            .order_by("-id")
        )
        evento = request.query_params.get("evento")
        if evento and evento.isdigit():
            qs = qs.filter(evento_id=int(evento))
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(nombre_legal__icontains=q) | Q(numero_documento__icontains=q))

        total = qs.count()
        page = max(_a_int(request.query_params.get("page")) or 1, 1)
        size = 50
        start = (page - 1) * size
        results = [{
            "id": c.id,
            "nombre_legal": c.nombre_legal,
            "numero_documento": c.numero_documento,
            "evento_id": c.evento_id,
            "evento_nombre": c.evento.nombre if c.evento_id else None,
            "estado": c.estado,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in qs[start:start + size]]
        return Response({"count": total, "page": page, "page_size": size, "results": results})


def _a_bool(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    return str(valor).strip().lower() in ("1", "true", "on", "si", "sí", "yes")


def _a_int(valor):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None
