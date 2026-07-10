"""Encuesta de percepción del festival — endpoints público + insights.

Público (AllowAny, por QR): el asistente ve el cuestionario y lo envía.
Gate: SOLO si el festival está `publicado=True` ("publicar = activar la
encuesta", decisión Alex 2026-07-10). Mismo criterio que la ficha pública.

Insights (organizador, módulo `festivales`): total de respuestas + desglose
por opción de cada pregunta de calificación (data-driven).
"""
import logging

from django.db import IntegrityError, connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.festivales.models import Festival, FestivalPercepcion
from apps.festivales.services.percepcion_schema import (
    PERCEPCION_SCHEMA, PREGUNTAS_CALIFICACION,
)

logger = logging.getLogger(__name__)

_PERMS = [ModuloRequiredPermission("festivales")]


def _festival_publicado(slug):
    return (Festival.objects
            .filter(slug=slug, publicado=True)
            .select_related("tipo_festival").first())


class PercepcionSchemaPublicView(APIView):
    """GET esquema + datos del festival para el formulario público."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        f = _festival_publicado(slug)
        if f is None:
            return Response(
                {"detail": "Este festival no está publicado o no existe.", "abierto": False},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "festival": {
                "id": f.id,
                "nombre": f.nombre,
                "tipo": (f.tipo_festival.nombre if f.tipo_festival_id else None),
                "vigencia": f.vigencia,
                "abierto": True,
            },
            "titulo": PERCEPCION_SCHEMA["titulo"],
            "objetivo": PERCEPCION_SCHEMA["objetivo"],
            "campos": PERCEPCION_SCHEMA["campos"],
        })


class PercepcionSubmitPublicView(APIView):
    """POST crea una respuesta de percepción (solo si el festival está publicado)."""
    permission_classes = [AllowAny]

    def post(self, request, slug):
        f = _festival_publicado(slug)
        if f is None:
            return Response(
                {"detail": "Esta encuesta no está disponible (festival no publicado)."},
                status=status.HTTP_410_GONE,
            )

        data = request.data
        datos = {}
        fijos = {"numero_documento": None, "nombre": None}
        errores = {}

        for campo in PERCEPCION_SCHEMA["campos"]:
            nombre = campo["name"]
            raw = data.get(nombre)
            valor = raw.strip() if isinstance(raw, str) else raw
            if campo.get("required") and not valor:
                errores[nombre] = ["Este campo es obligatorio."]
                continue
            if valor not in (None, ""):
                datos[nombre] = valor
                mapa = campo.get("map_to")
                if mapa in fijos:
                    fijos[mapa] = valor

        if errores:
            return Response(
                {"detail": "Hay campos obligatorios sin completar.", "errors": errores},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            obj = FestivalPercepcion.objects.create(
                festival_id=f.id, datos=datos,
                numero_documento=fijos["numero_documento"],
                nombre=fijos["nombre"],
            )
        except IntegrityError:
            # Índice parcial único (festival_id, numero_documento).
            return Response(
                {"detail": "Ya registramos una respuesta con esta cédula para este festival.",
                 "errors": {"numero_documento": ["Ya respondiste esta encuesta."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"id": obj.id, "ok": True}, status=status.HTTP_201_CREATED)


class PercepcionQRView(APIView):
    """GET URL pública + QR (PNG base64) de la encuesta del festival.

    Solo tiene sentido cuando el festival está publicado (ahí existe el slug).
    """
    permission_classes = _PERMS

    def get(self, request, fid):
        import base64
        import io

        import qrcode

        from apps.login.services.scope import aplicar_subgrupo

        fest = aplicar_subgrupo(
            Festival.objects.all(), request.user, campo="subgrupo_id"
        ).filter(pk=fid).first()
        if fest is None:
            return Response({"detail": "Festival no encontrado."}, status=404)

        if not fest.publicado or not fest.slug:
            return Response({"publicado": False, "url": None, "path": None, "qr_base64": None})

        path = f"/app/p/festival-percepcion/{fest.slug}"
        url = request.build_absolute_uri(path)
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()
        return Response({"publicado": True, "url": url, "path": path, "qr_base64": qr_base64})


class PercepcionInsightsView(APIView):
    """GET total + desglose por opción de cada pregunta de calificación."""
    permission_classes = _PERMS

    def get(self, request, fid):
        from collections import Counter
        from apps.login.services.scope import aplicar_subgrupo

        # RBAC: el usuario solo ve festivales de su alcance.
        fest = aplicar_subgrupo(
            Festival.objects.all(), request.user, campo="subgrupo_id"
        ).filter(pk=fid).first()
        if fest is None:
            return Response({"detail": "Festival no encontrado."}, status=404)

        filas = list(FestivalPercepcion.objects.filter(festival_id=fid).values_list("datos", flat=True))
        total = len(filas)

        def dist(campo, etiquetas=None):
            cont = Counter()
            for d in filas:
                v = (d or {}).get(campo)
                if v:
                    cont[str(v)] += 1
            orden = etiquetas or [k for k, _ in cont.most_common()]
            return [{"label": k, "valor": cont.get(k, 0)} for k in orden if cont.get(k, 0) or etiquetas]

        escala = ["Excelente", "Bueno", "Regular", "Malo"]
        preguntas = []
        etiqueta = {c["name"]: c["label"] for c in PERCEPCION_SCHEMA["campos"]}
        for name in PREGUNTAS_CALIFICACION:
            preguntas.append({
                "campo": name, "label": etiqueta.get(name, name),
                "datos": dist(name, escala),
            })

        return Response({
            "festival": {"id": fest.id, "nombre": fest.nombre, "publicado": fest.publicado, "slug": fest.slug},
            "total": total,
            "preguntas": preguntas,
            "genero": dist("genero"),
            "rango_edad": dist("rango_edad", ["18 - 25 años", "26 - 40 años", "41 - 60 años", "Más de 60 años"]),
        })
