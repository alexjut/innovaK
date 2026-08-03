"""Encuesta de percepción del festival — endpoints público + insights.

Público (AllowAny, por QR): el asistente ve el cuestionario y lo envía.
Gate: SOLO si el festival está `publicado=True` ("publicar = activar la
encuesta", decisión Alex 2026-07-10). Mismo criterio que la ficha pública.

Insights (organizador, módulo `festivales`): total de respuestas + desglose
por opción de cada pregunta de calificación (data-driven).
"""
import logging
from datetime import date, timedelta

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

# La encuesta se cierra sola este número de días DESPUÉS de la fecha de fin
# del festival (decisión Alex 2026-07-10). Si el festival no tiene fecha de
# fin, solo cierra al despublicar.
DIAS_GRACIA_CIERRE = 1


def _festival_publicado(slug):
    return (Festival.objects
            .filter(slug=slug, publicado=True)
            .select_related("tipo_festival").first())


def _abierta(f) -> bool:
    """Abierta si está publicada y no pasó la ventana tras la fecha de fin."""
    if not f.publicado:
        return False
    if f.fecha_fin and date.today() > f.fecha_fin + timedelta(days=DIAS_GRACIA_CIERRE):
        return False
    return True


def _mensaje_cierre(f) -> str:
    if f.fecha_fin:
        cierre = f.fecha_fin + timedelta(days=DIAS_GRACIA_CIERRE)
        return f"La encuesta de este festival cerró el {cierre.isoformat()}."
    return "Esta encuesta ya no está disponible."


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
        abierta = _abierta(f)
        return Response({
            "festival": {
                "id": f.id,
                "nombre": f.nombre,
                "tipo": (f.tipo_festival.nombre if f.tipo_festival_id else None),
                "vigencia": f.vigencia,
                "abierto": abierta,
            },
            "mensaje": None if abierta else _mensaje_cierre(f),
            "titulo": PERCEPCION_SCHEMA["titulo"],
            "objetivo": PERCEPCION_SCHEMA["objetivo"],
            "campos": PERCEPCION_SCHEMA["campos"],
        })


class PercepcionAbiertasPublicView(APIView):
    """GET las encuestas de percepción ABIERTAS ahora mismo. Público.

    Existe por el home público (`/app/`): hasta ahora a la encuesta solo se
    llegaba escaneando el QR del festival, así que quien entra por la web no
    tenía forma de saber cuáles están abiertas. Esto no relaja ningún gate —
    aplica exactamente el mismo criterio que el formulario (`_abierta`), y solo
    expone lo que ya es público en la ficha: nombre, tipo, fechas y slug.

    Nada de responsable, subgrupo ni conteo de respuestas: eso es del
    organizador y va por los endpoints con módulo `festivales`.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        festivales = (Festival.objects
                      .filter(publicado=True)
                      .exclude(slug__isnull=True).exclude(slug="")
                      .select_related("tipo_festival")
                      .order_by("-vigencia", "nombre"))
        abiertas = [{
            "slug": f.slug,
            "nombre": f.nombre,
            "tipo": (f.tipo_festival.nombre if f.tipo_festival_id else None),
            "vigencia": f.vigencia,
            "fecha_inicio": f.fecha_inicio.isoformat() if f.fecha_inicio else None,
            "fecha_fin": f.fecha_fin.isoformat() if f.fecha_fin else None,
            "lugar": f.lugar_texto or None,
        } for f in festivales if _abierta(f)]
        return Response({"encuestas": abiertas, "total": len(abiertas)})


class PercepcionSubmitPublicView(APIView):
    """POST crea una respuesta de percepción (solo si el festival está publicado)."""
    permission_classes = [AllowAny]

    def post(self, request, slug):
        f = _festival_publicado(slug)
        if f is None or not _abierta(f):
            return Response(
                {"detail": _mensaje_cierre(f) if f else "Esta encuesta no está disponible."},
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
        # El sitio público se sirve por HTTPS (ngrok/prod); nginx→gunicorn es
        # http, así que build_absolute_uri arma http://. Forzamos https salvo
        # en local, para que el QR abra sin advertencia de "sitio no seguro".
        host = request.get_host()
        if url.startswith("http://") and not (host.startswith("localhost") or host.startswith("127.")):
            url = "https://" + url[len("http://"):]
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
            "festival": {"id": fest.id, "nombre": fest.nombre, "publicado": fest.publicado,
                         "slug": fest.slug, "abierta": _abierta(fest),
                         "cierre_msg": None if _abierta(fest) else _mensaje_cierre(fest)},
            "total": total,
            "preguntas": preguntas,
            "genero": dist("genero"),
            "rango_edad": dist("rango_edad", ["18 - 25 años", "26 - 40 años", "41 - 60 años", "Más de 60 años"]),
        })
