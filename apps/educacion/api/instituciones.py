"""API del catálogo de instituciones de educación posmedia.

DRF con `ModuloRequiredPermission("educacion")`, que además bloquea la escritura
a los roles de solo lectura (RBAC B0).

**Todo lo que devuelve son AGREGADOS.** Conteos por institución, por programa y
por nivel; ningún listado de personas identificadas, para ningún rol —tampoco
para quien tenga `datos_personales`—. Un mapa se proyecta en reuniones y se
captura en pantalla: es una superficie de exposición distinta a la de una ficha.

**No es público**, a diferencia de las capas del mapa de la localidad: acá se
cuentan beneficiarios de un programa social por institución, y eso no es
información para el ciudadano anónimo.
"""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.educacion.models import InstitucionEducativa, ProgramaAcademico
from apps.educacion.services import instituciones as svc
from apps.jovenes_a_la_e.services.cargue_excel import digitos
from apps.login.api.permissions import ModuloRequiredPermission

logger = logging.getLogger(__name__)

_PERMS = [ModuloRequiredPermission("educacion")]


def _vigencia(request) -> int | None:
    """El filtro de vigencia. Sin él, «acumulado» — que NO es la suma de años."""
    v = (request.query_params.get("vigencia") or "").strip()
    return int(v) if v.isdigit() else None


def _json(inst: InstitucionEducativa, conteo: dict | None = None) -> dict:
    conteo = conteo or {}
    return {
        "id": inst.id,
        "codigo_snies": inst.codigo_snies,
        "nombre": inst.nombre,
        "tipo_registro": inst.tipo_registro,
        "ciudad": inst.ciudad,
        "latitud": float(inst.latitud) if inst.latitud is not None else None,
        "longitud": float(inst.longitud) if inst.longitud is not None else None,
        "ubicada": inst.ubicada,
        "origen": inst.origen,
        "activa": inst.activa,
        "observacion": inst.observacion,
        "personas": conteo.get("personas", 0),
        "matriculas": conteo.get("matriculas", 0),
        "programas": conteo.get("programas", 0),
    }


class InstitucionListView(APIView):
    """GET lista con conteos · POST alta manual."""
    permission_classes = _PERMS

    def get(self, request):
        vigencia = _vigencia(request)
        conteos = svc.conteos_por_institucion(vigencia)
        qs = InstitucionEducativa.objects.all()
        if request.query_params.get("sin_ubicar") == "1":
            qs = qs.filter(latitud__isnull=True)
        if request.query_params.get("tipo"):
            qs = qs.filter(tipo_registro=request.query_params["tipo"])

        items = [_json(i, conteos.get(i.codigo_snies)) for i in qs]
        # Ordenadas por beneficiarios: la pregunta del área es «dónde están los
        # míos», no el alfabeto.
        items.sort(key=lambda x: (-x["personas"], x["nombre"]))
        return Response({
            "instituciones": items,
            "vigencia": vigencia,
            "vigencias": svc.vigencias_disponibles(),
            "desglose_nivel": svc.desglose_por_nivel(vigencia),
            "sin_ubicar": sum(1 for i in items if not i["ubicada"]),
            # El dato de origen trae el SNIES de la INSTITUCIÓN, no la sede
            # donde estudia cada persona. El punto es la sede principal y la UI
            # tiene que decirlo, o se lee como «estos estudian aquí».
            "precision": (
                "El punto es la sede principal de la institución: el archivo del "
                "área trae el código de la institución, no el de la sede donde "
                "estudia cada beneficiario."),
        })

    def post(self, request):
        codigo = digitos(request.data.get("codigo_snies"))
        nombre = (request.data.get("nombre") or "").strip()
        if not codigo:
            return Response({"detail": "El código SNIES/SIET debe ser numérico."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not nombre:
            return Response({"detail": "El nombre es obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        ya = InstitucionEducativa.objects.filter(codigo_snies=codigo).first()
        if ya:
            return Response(
                {"detail": f"El código {codigo} ya existe: «{ya.nombre}». "
                           "Edítela en vez de crear otra."},
                status=status.HTTP_400_BAD_REQUEST)

        inst = InstitucionEducativa.objects.create(
            codigo_snies=codigo, nombre=nombre, origen="MANUAL",
            tipo_registro=request.data.get("tipo_registro") or "SNIES",
            ciudad=(request.data.get("ciudad") or "").strip() or None,
            latitud=request.data.get("latitud") or None,
            longitud=request.data.get("longitud") or None,
        )
        return Response(_json(inst), status=status.HTTP_201_CREATED)


class InstitucionDetailView(APIView):
    """GET detalle con programas y alumnos por programa · PATCH corrección."""
    permission_classes = _PERMS

    def get(self, request, pk):
        inst = get_object_or_404(InstitucionEducativa, pk=pk)
        vigencia = _vigencia(request)
        conteos = svc.conteos_por_institucion(vigencia).get(inst.codigo_snies, {})
        por_programa = svc.conteos_por_programa(inst.codigo_snies, vigencia)

        programas = []
        for p in inst.programas.all():
            c = por_programa.get(p.codigo_snies, {})
            programas.append({
                "id": p.id, "codigo_snies": p.codigo_snies, "nombre": p.nombre,
                "nivel_formacion": p.nivel_formacion,
                "nivel_etiqueta": dict(ProgramaAcademico.NIVEL_CHOICES).get(
                    p.nivel_formacion, p.nivel_formacion),
                "personas": c.get("personas", 0),
                "matriculas": c.get("matriculas", 0),
            })
        programas.sort(key=lambda x: (-x["personas"], x["nombre"]))

        # Por vigencia, para ver la evolución sin sumar años (una persona en dos
        # vigencias es una, no dos).
        por_vigencia = {
            v: svc.conteos_por_institucion(v).get(inst.codigo_snies, {}).get("personas", 0)
            for v in svc.vigencias_disponibles()
        }
        return Response({**_json(inst, conteos),
                         "programas": programas,
                         "por_vigencia": por_vigencia,
                         "vigencia": vigencia})

    def patch(self, request, pk):
        inst = get_object_or_404(InstitucionEducativa, pk=pk)
        datos = request.data

        if "codigo_snies" in datos:
            return Response(
                {"detail": "El código no se edita: es la llave con la que se "
                           "cruzan los beneficiarios. Cree otra institución si el "
                           "código estaba mal y avísele al área."},
                status=status.HTTP_400_BAD_REQUEST)

        for campo in ("nombre", "ciudad", "observacion", "tipo_registro"):
            if campo in datos:
                setattr(inst, campo, (datos.get(campo) or "").strip() or None)
        if "activa" in datos:
            inst.activa = bool(datos["activa"])

        # Las coordenadas van juntas o no van: media coordenada no ubica nada, y
        # la base lo rechaza con un CHECK.
        if "latitud" in datos or "longitud" in datos:
            lat, lon = datos.get("latitud"), datos.get("longitud")
            if (lat in (None, "")) != (lon in (None, "")):
                return Response(
                    {"detail": "Latitud y longitud van juntas: con una sola no se "
                               "puede ubicar el punto."},
                    status=status.HTTP_400_BAD_REQUEST)
            inst.latitud = lat or None
            inst.longitud = lon or None

        if not inst.nombre:
            return Response({"detail": "El nombre no puede quedar vacío."},
                            status=status.HTTP_400_BAD_REQUEST)
        inst.save()
        return Response(_json(inst))


class InstitucionGeojsonView(APIView):
    """GET — las ubicadas, como FeatureCollection para el mapa.

    Las SIN ubicar no van acá (no hay dónde pintarlas) pero su cantidad sí
    viaja: una institución que no aparece en el mapa se lee como «no existe» en
    vez de «no sabemos dónde queda». Mismo criterio que la capa de colegios.
    """
    permission_classes = _PERMS

    def get(self, request):
        vigencia = _vigencia(request)
        conteos = svc.conteos_por_institucion(vigencia)
        features, sin_ubicar = [], 0
        for i in InstitucionEducativa.objects.filter(activa=True):
            if not i.ubicada:
                sin_ubicar += 1
                continue
            c = conteos.get(i.codigo_snies, {})
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [float(i.longitud), float(i.latitud)]},
                "properties": {
                    "id": i.id, "codigo_snies": i.codigo_snies, "nombre": i.nombre,
                    "tipo_registro": i.tipo_registro, "ciudad": i.ciudad,
                    "personas": c.get("personas", 0),
                    "programas": c.get("programas", 0),
                },
            })
        return Response({"type": "FeatureCollection", "features": features,
                         "sin_ubicar": sin_ubicar, "vigencia": vigencia})


class InstitucionSincronizarView(APIView):
    """POST — da de alta lo que aparezca en los cargues y no exista.

    Seco salvo que se mande `aplicar=true`: crea filas de catálogo y conviene
    ver antes qué haría, sobre todo por los avisos de códigos y nombres que no
    cuadran.
    """
    permission_classes = _PERMS

    def post(self, request):
        aplicar = str(request.data.get("aplicar", "")).lower() in ("1", "true", "si", "sí")
        try:
            return Response(svc.sincronizar_desde_entregas(aplicar=aplicar))
        except Exception:  # noqa: BLE001
            logger.exception("Fallo sincronizando el catálogo de instituciones")
            return Response({"detail": "No se pudo sincronizar el catálogo."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
