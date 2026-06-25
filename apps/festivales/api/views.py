"""API DRF del módulo Festivales (interno, autenticado).

Gating: módulo `festivales`. CRUD de la cabecera de festival + catálogos.
La galería/aforo/jurados/evaluación/publicación llegan en PR-2..PR-5.
"""
import logging

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission

from apps.festivales.models import Festival, FestivalArchivo, FestivalDia, TipoFestival
from apps.festivales.api.serializers import (
    FestivalArchivoSerializer,
    FestivalDetailSerializer,
    FestivalDiaConActosSerializer,
    FestivalDiaSerializer,
    FestivalSerializer,
    TipoFestivalSerializer,
)

logger = logging.getLogger(__name__)

# Límite de subida de evidencias (videos incluidos). 50 MB.
MAX_ARCHIVO_BYTES = 50 * 1024 * 1024
# Tope de fotos por festival (por ahora; configurable). Las fotos se
# optimizan antes de cifrarse a Mongo (ver services/imagen.py).
MAX_FOTOS_FESTIVAL = 3

_PERMS = [ModuloRequiredPermission("festivales")]


class FestivalListCreateView(APIView):
    """GET lista (filtros vigencia/estado/tipo) · POST crea."""

    permission_classes = _PERMS

    def get(self, request):
        # RBAC PR-4: scope por subgrupo (superuser ve todo; resto solo el suyo).
        from apps.login.services.scope import aplicar_subgrupo
        qs = aplicar_subgrupo(
            Festival.objects.select_related("tipo_festival").all(),
            request.user, campo="subgrupo_id")
        vig = request.query_params.get("vigencia")
        if vig and vig.isdigit():
            qs = qs.filter(vigencia=int(vig))
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        tipo = request.query_params.get("tipo")
        if tipo and tipo.isdigit():
            qs = qs.filter(tipo_festival_id=int(tipo))
        return Response(FestivalSerializer(qs, many=True).data)

    def post(self, request):
        ser = FestivalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class FestivalDetailView(APIView):
    """GET detalle · PATCH edita · DELETE elimina."""

    permission_classes = _PERMS

    def _obj(self, pk):
        return Festival.objects.select_related("tipo_festival").filter(pk=pk).first()

    def _denegado(self, request, obj):
        """403 si el festival pertenece a un subgrupo no visible para el usuario."""
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(request.user)
        if subs is not None and obj.subgrupo_id not in subs:
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        return None

    def get(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        denegado = self._denegado(request, obj)
        if denegado is not None:
            return denegado
        return Response(FestivalDetailSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        denegado = self._denegado(request, obj)
        if denegado is not None:
            return denegado
        estado_antes = obj.estado
        ser = FestivalSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        # Si cambió el estado, alinea el avance del KPI (acto suma +1).
        if obj.estado != estado_antes:
            from apps.festivales.services.avance import sincronizar_festival
            try:
                sincronizar_festival(obj)
            except Exception:
                logger.exception("Error sincronizando avance del festival %s", pk)
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        denegado = self._denegado(request, obj)
        if denegado is not None:
            return denegado
        if obj.eventos.exists():
            return Response(
                {"detail": "No se puede eliminar: el festival tiene actos (eventos) asociados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FestivalPublicarView(APIView):
    """`POST /festivales/api/festivales/<pk>/publicar/` — publica/despublica.

    Al publicar genera el slug (si falta) y marca `publicado_en`. La ficha
    pública queda en `/app/p/festival/<slug>`.
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        from django.utils import timezone
        from django.utils.text import slugify
        obj = Festival.objects.filter(pk=pk).first()
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        publicar = bool(request.data.get("publicado", not obj.publicado))
        if publicar and not obj.slug:
            base = slugify(f"{obj.nombre}-{obj.vigencia}") or f"festival-{obj.id}"
            slug = base
            i = 2
            while Festival.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            obj.slug = slug
        obj.publicado = publicar
        obj.publicado_en = timezone.now() if publicar else None
        obj.save(update_fields=["publicado", "publicado_en", "slug"])
        return Response({"publicado": obj.publicado, "slug": obj.slug,
                         "url": f"/app/p/festival/{obj.slug}" if obj.slug else None})


class FestivalCatalogosView(APIView):
    """GET catálogos para los formularios (tipos + vigencias + estados)."""

    permission_classes = _PERMS

    def get(self, request):
        tipos = TipoFestival.objects.filter(activo=True)
        # order_by() limpia el ordering del Meta (que arrastra `nombre` al
        # SELECT y rompe el distinct → vigencias duplicadas).
        vigencias = sorted(
            Festival.objects.order_by().values_list("vigencia", flat=True).distinct(),
            reverse=True,
        )
        # Resumen de avance por estado (FEST-F-07): planeados vs ejecutados
        # contra la meta anual. Se filtra por la vigencia pedida (o la más
        # reciente con datos) para que el KPI refleje el año en pantalla.
        vig = request.query_params.get("vigencia")
        vig = int(vig) if vig and vig.isdigit() else (vigencias[0] if vigencias else None)
        resumen_qs = Festival.objects.all()
        if vig is not None:
            resumen_qs = resumen_qs.filter(vigencia=vig)
        conteo = {estado: 0 for estado, _ in Festival.ESTADOS}
        for estado in resumen_qs.values_list("estado", flat=True):
            if estado in conteo:
                conteo[estado] += 1
        # UPLs de Kennedy (reusa el catálogo del Banco) para escoger el área
        # del festival de forma estructurada (FEST-F-11). El punto exacto se
        # captura aparte (latitud/longitud) y alimenta el marcador en el mapa.
        try:
            from apps.banco_iniciativas.models import Upl
            upls = [
                {"value": u.codigo, "label": u.nombre}
                for u in Upl.objects.filter(activo=True).order_by("orden", "nombre")
            ]
        except Exception:
            upls = []
        # Funcionarios activos para escoger el responsable (festival o día).
        # Mismo patrón dedup-por-persona que DocentesDisponiblesView.
        responsables = []
        try:
            from apps.login.models.funcionario import Funcionario
            vistos = set()
            for f in (Funcionario.objects.filter(activo=True)
                      .select_related("persona").order_by("persona__apellido1")[:500]):
                if f.persona_id in vistos:
                    continue
                vistos.add(f.persona_id)
                p = f.persona
                nombre = (f"{p.nombre1 or ''} {p.apellido1 or ''}".strip() if p else "")
                responsables.append({"value": f.id, "label": nombre or f"Funcionario #{f.id}"})
        except Exception:
            responsables = []
        return Response({
            "tipos_festival": TipoFestivalSerializer(tipos, many=True).data,
            "vigencias": list(vigencias),
            "estados": [{"value": v, "label": l} for v, l in Festival.ESTADOS],
            "upls": upls,
            "responsables": responsables,
            "max_fotos": MAX_FOTOS_FESTIVAL,
            "tipos_archivo": [{"value": t, "label": l} for t, l in FestivalArchivo.TIPOS],
            "resumen": {
                "vigencia": vig,
                "planeados": conteo.get(Festival.PLANEADO, 0),
                "ejecutados": conteo.get(Festival.EJECUTADO, 0),
                "cerrados": conteo.get(Festival.CERRADO, 0),
                "meta_anual": 15,
            },
        })


class FestivalGeoJSONView(APIView):
    """`GET /festivales/api/festivales/geojson/` — festivales con coordenadas
    como FeatureCollection, para el layer del Mapa Kennedy (FEST-F-11).

    Solo incluye los que tienen latitud/longitud. Filtros opcionales:
      tipo_festival   código (repetible)
      vigencia        int
      estado          código de estado
    Gating: cualquier usuario autenticado (como EventoGeoJSONView), para que
    el layer cargue aunque el usuario no tenga el módulo `festivales`.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (Festival.objects
              .select_related("tipo_festival")
              .filter(latitud__isnull=False, longitud__isnull=False))

        tipos = request.query_params.getlist("tipo_festival")
        if tipos:
            try:
                qs = qs.filter(tipo_festival_codigo__in=[int(x) for x in tipos])
            except ValueError:
                pass
        vig = request.query_params.get("vigencia")
        if vig and vig.isdigit():
            qs = qs.filter(vigencia=int(vig))
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        features = [{
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(f.longitud), float(f.latitud)],
            },
            "properties": {
                "id": f.id,
                "nombre": f.nombre,
                "tipo_festival": (f.tipo_festival.nombre if f.tipo_festival_id else None),
                "vigencia": f.vigencia,
                "estado": f.get_estado_display(),
                "fecha_inicio": f.fecha_inicio.isoformat() if f.fecha_inicio else None,
                "fecha_fin": f.fecha_fin.isoformat() if f.fecha_fin else None,
                "lugar": f.lugar_texto,
                "n_eventos": f.eventos.count(),
            },
        } for f in qs]

        return Response({
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        })


# ── PR-A · Programación multi-día ────────────────────────────────────────

class FestivalDiaListCreateView(APIView):
    """`/festivales/api/festivales/<fid>/dias/` — agenda de días del festival.

    GET  lista los días (con sus actos embebidos).
    POST crea un día (la cabecera viene en la URL, no en el body).
    """
    permission_classes = _PERMS

    def get(self, request, fid):
        if not Festival.objects.filter(pk=fid).exists():
            return Response({"detail": "Festival no encontrado."}, status=404)
        dias = (FestivalDia.objects.filter(festival_id=fid)
                .select_related("responsable__persona"))
        return Response(FestivalDiaConActosSerializer(dias, many=True).data)

    def post(self, request, fid):
        if not Festival.objects.filter(pk=fid).exists():
            return Response({"detail": "Festival no encontrado."}, status=404)
        data = {**request.data, "festival": fid}
        ser = FestivalDiaSerializer(data=data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class FestivalDiaDetailView(APIView):
    """`/festivales/api/dias/<id>/` — PATCH edita · DELETE elimina un día."""

    permission_classes = _PERMS

    def _obj(self, pk):
        return (FestivalDia.objects.select_related("responsable__persona")
                .filter(pk=pk).first())

    def patch(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Día no encontrado."}, status=404)
        # No se permite mover el día a otro festival desde aquí.
        data = {k: v for k, v in request.data.items() if k != "festival"}
        ser = FestivalDiaSerializer(obj, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Día no encontrado."}, status=404)
        # Los actos del día NO se borran: quedan en el festival sin día
        # (evento.festival_dia_id → NULL por la FK ON DELETE SET NULL).
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActoDiaView(APIView):
    """`/festivales/api/actos/<evento_id>/dia/` — ubica un acto en la agenda.

    PATCH body `{"festival_dia_id": <id|null>}`:
      · id   → mueve el acto a ese día (y al festival del día).
      · null → saca el acto de la agenda (queda en el festival sin día).
    """
    permission_classes = _PERMS

    def patch(self, request, evento_id):
        from apps.login.models import Evento
        acto = Evento.objects.filter(pk=evento_id).first()
        if acto is None:
            return Response({"detail": "Acto (evento) no encontrado."}, status=404)
        if "festival_dia_id" not in request.data:
            return Response({"detail": "Falta festival_dia_id."},
                            status=status.HTTP_400_BAD_REQUEST)
        dia_id = request.data.get("festival_dia_id")
        if dia_id in (None, "", "null"):
            acto.festival_dia = None
            acto.save(update_fields=["festival_dia"])
            return Response({"evento_id": acto.id, "festival_dia_id": None})
        dia = FestivalDia.objects.filter(pk=dia_id).first()
        if dia is None:
            return Response({"detail": "Día no encontrado."},
                            status=status.HTTP_400_BAD_REQUEST)
        # El acto queda atado al día y, por coherencia, al festival del día.
        acto.festival_dia = dia
        acto.festival_id = dia.festival_id
        acto.save(update_fields=["festival_dia", "festival"])
        return Response({"evento_id": acto.id, "festival_dia_id": dia.id,
                         "festival_id": dia.festival_id})


class ActoAforoProyectadoView(APIView):
    """`PATCH /festivales/api/actos/<evento_id>/aforo-proyectado/` — fija la
    meta de aforo del acto. Body `{"aforo_proyectado": <int|null>}`."""

    permission_classes = _PERMS

    def patch(self, request, evento_id):
        from apps.login.models import Evento
        acto = Evento.objects.filter(pk=evento_id).first()
        if acto is None:
            return Response({"detail": "Acto no encontrado."}, status=404)
        val = request.data.get("aforo_proyectado")
        if val in (None, "", "null"):
            acto.aforo_proyectado = None
        else:
            try:
                acto.aforo_proyectado = max(0, int(val))
            except (TypeError, ValueError):
                return Response({"detail": "aforo_proyectado debe ser entero."},
                                status=status.HTTP_400_BAD_REQUEST)
        acto.save(update_fields=["aforo_proyectado"])
        return Response({"evento_id": acto.id, "aforo_proyectado": acto.aforo_proyectado})


# ── PR-C · Tablero de seguimiento (avance real al KPI + presupuesto) ─────

class FestivalInsightsView(APIView):
    """`/festivales/api/festivales/insights/?vigencia=` — tablero del módulo.

    Conexión NO decorativa con la Meta 4 del 2780: lee el avance real de los
    KPIs (presu_avance_ind_periodo) y el presupuesto del proyecto. Reusa
    `presupuesto.services.metrics.resumen_inversion`.
    """
    permission_classes = _PERMS
    PROYECTO_ID = 1  # 2780 "KENNEDY PROYECTA TALENTO"

    def get(self, request):
        from apps.presupuesto.models import ActividadIndicador, AvanceIndicador, Indicador

        vigencias = sorted(
            Festival.objects.order_by().values_list("vigencia", flat=True).distinct(),
            reverse=True,
        )
        vig = request.query_params.get("vigencia")
        vig = int(vig) if vig and vig.isdigit() else (vigencias[0] if vigencias else None)

        fests = list(
            Festival.objects.filter(vigencia=vig).select_related("tipo_festival")
            if vig is not None else Festival.objects.none()
        )

        from apps.festivales.models import FestivalAsistencia

        # Resumen por festival + actos por estado.
        festivales = []
        conteo_estado = {e: 0 for e, _ in Festival.ESTADOS}
        total_actos = actos_contabilizados = aforo_total = 0
        actividad_plan_ids = set()
        for f in fests:
            actos = list(f.eventos.all())
            n_actos = len(actos)
            total_actos += n_actos
            if f.estado in (Festival.EJECUTADO, Festival.CERRADO):
                actos_contabilizados += n_actos
            conteo_estado[f.estado] = conteo_estado.get(f.estado, 0) + 1
            for a in actos:
                if a.actividad_plan_id:
                    actividad_plan_ids.add(a.actividad_plan_id)
            aforo_f = FestivalAsistencia.objects.filter(festival_id=f.id).count()
            aforo_total += aforo_f
            festivales.append({
                "id": f.id, "nombre": f.nombre, "estado": f.estado,
                "estado_display": f.get_estado_display(),
                "tipo": (f.tipo_festival.nombre if f.tipo_festival_id else None),
                "n_actos": n_actos, "n_dias": f.dias.count(),
                "n_archivos": f.archivos.count(),
                "aforo": aforo_f,
            })

        # KPIs ligados a las actividades de esos actos + avance real.
        kpis = []
        if actividad_plan_ids:
            ind_ids = set(
                ActividadIndicador.objects
                .filter(actividad_plan_id__in=actividad_plan_ids, activo=True)
                .values_list("indicador_id", flat=True)
            )
            for ind in Indicador.objects.filter(id__in=ind_ids):
                avances = AvanceIndicador.objects.filter(indicador_id=ind.id)
                total = sum(float(a.magnitud_aportada or 0) for a in avances)
                de_fest = sum(
                    float(a.magnitud_aportada or 0) for a in avances
                    if a.observaciones and "festival=" in a.observaciones
                )
                meta = float(ind.meta_magnitud or 0)
                kpis.append({
                    "id": ind.id, "nombre": ind.nombre,
                    "unidad": ind.unidad_medida,
                    "meta_magnitud": meta,
                    "avance_total": total,
                    "avance_festivales": de_fest,
                    "pct": round(total / meta * 100, 1) if meta else None,
                })

        # Presupuesto del proyecto 2780 (asignado vs comprometido).
        try:
            from apps.presupuesto.services.metrics import resumen_inversion
            inv = resumen_inversion({"proyecto_id": self.PROYECTO_ID})
            presupuesto = {
                "asignado": inv.get("asignado_total", 0),
                "ejecutado": inv.get("comprometido_total", 0),
                "disponible": inv.get("disponible_total", 0),
            }
        except Exception:
            logger.exception("Error leyendo presupuesto del proyecto %s", self.PROYECTO_ID)
            presupuesto = {"asignado": 0, "ejecutado": 0, "disponible": 0}

        return Response({
            "vigencia": vig,
            "vigencias": vigencias,
            "festivales": festivales,
            "kpis": kpis,
            "presupuesto": presupuesto,
            "resumen": {
                "n_festivales": len(fests),
                "planeados": conteo_estado.get(Festival.PLANEADO, 0),
                "ejecutados": conteo_estado.get(Festival.EJECUTADO, 0),
                "cerrados": conteo_estado.get(Festival.CERRADO, 0),
                "total_actos": total_actos,
                "actos_contabilizados": actos_contabilizados,
                "aforo_total": aforo_total,
            },
        })


# ── PR-B · Biblioteca / evidencias ───────────────────────────────────────

class FestivalBibliotecaView(APIView):
    """`/festivales/api/festivales/<fid>/biblioteca/` — evidencias del festival.

    GET  lista los archivos (metadata + URL de descarga). Filtros opcionales:
         tipo, dia (festival_dia_id).
    POST sube un archivo (multipart): file, tipo, festival_dia_id?, descripcion?.
         El binario va CIFRADO a Mongo; aquí queda el puntero + metadata.
    """
    permission_classes = _PERMS
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, fid):
        if not Festival.objects.filter(pk=fid).exists():
            return Response({"detail": "Festival no encontrado."}, status=404)
        qs = (FestivalArchivo.objects.filter(festival_id=fid)
              .select_related("festival_dia", "subido_por__persona"))
        tipo = request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        dia = request.query_params.get("dia")
        if dia and dia.isdigit():
            qs = qs.filter(festival_dia_id=int(dia))
        return Response(FestivalArchivoSerializer(qs, many=True).data)

    def post(self, request, fid):
        festival = Festival.objects.filter(pk=fid).first()
        if festival is None:
            return Response({"detail": "Festival no encontrado."}, status=404)

        archivo = request.FILES.get("file")
        if archivo is None:
            return Response({"detail": "Falta el archivo (campo 'file')."},
                            status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_ARCHIVO_BYTES:
            return Response(
                {"detail": f"El archivo supera el máximo permitido "
                           f"({MAX_ARCHIVO_BYTES // (1024 * 1024)} MB)."},
                status=status.HTTP_400_BAD_REQUEST)

        tipo = (request.data.get("tipo") or FestivalArchivo.FOTO).strip()
        if tipo not in {t for t, _ in FestivalArchivo.TIPOS}:
            return Response({"detail": f"Tipo inválido: {tipo}."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Tope de fotos por festival (por ahora).
        if tipo == FestivalArchivo.FOTO:
            n_fotos = FestivalArchivo.objects.filter(
                festival_id=fid, tipo=FestivalArchivo.FOTO).count()
            if n_fotos >= MAX_FOTOS_FESTIVAL:
                return Response(
                    {"detail": f"Máximo {MAX_FOTOS_FESTIVAL} fotos por festival "
                               f"(ya hay {n_fotos}). Borra una para subir otra."},
                    status=status.HTTP_400_BAD_REQUEST)

        # Día opcional; si viene, debe pertenecer al festival.
        dia_id = request.data.get("festival_dia_id")
        dia = None
        if dia_id not in (None, "", "null"):
            dia = FestivalDia.objects.filter(pk=dia_id, festival_id=fid).first()
            if dia is None:
                return Response({"detail": "El día no pertenece a este festival."},
                                status=status.HTTP_400_BAD_REQUEST)

        blob = archivo.read()
        mime = archivo.content_type or "application/octet-stream"
        # Optimiza imágenes (resize + JPEG progresivo) antes de cifrar: nada
        # de fotos crudas de celular ocupando el almacenamiento cifrado.
        from apps.festivales.services import imagen as imagen_svc
        if tipo == FestivalArchivo.FOTO or imagen_svc.es_imagen(mime):
            try:
                blob, mime = imagen_svc.optimizar(blob)
            except Exception:
                return Response(
                    {"detail": "El archivo no es una imagen válida."},
                    status=status.HTTP_400_BAD_REQUEST)

        # Cifra y persiste el binario en Mongo. Si Mongo falla, NO se crea fila.
        from apps.documentos.services import mongo_storage
        try:
            mongo_id = mongo_storage.guardar(blob, mime, owner={
                "tipo": "festival_archivo",
                "festival_id": fid,
                "campo": tipo,
            })
        except Exception:
            logger.exception("Error cifrando evidencia de festival %s a Mongo", fid)
            return Response(
                {"detail": "No se pudo guardar el archivo (almacenamiento cifrado)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        nombre = archivo.name
        if mime == "image/jpeg" and nombre and not nombre.lower().endswith((".jpg", ".jpeg")):
            nombre = nombre.rsplit(".", 1)[0] + ".jpg"
        obj = FestivalArchivo.objects.create(
            festival=festival,
            festival_dia=dia,
            tipo=tipo,
            mongo_id=mongo_id,
            nombre_archivo=nombre,
            mime=mime,
            tamano_bytes=len(blob),
            descripcion=(request.data.get("descripcion") or "").strip() or None,
        )
        return Response(FestivalArchivoSerializer(obj).data,
                        status=status.HTTP_201_CREATED)


class FestivalArchivoDetailView(APIView):
    """`/festivales/api/biblioteca/<id>/` — DELETE borra la evidencia."""

    permission_classes = _PERMS

    def delete(self, request, pk):
        obj = FestivalArchivo.objects.filter(pk=pk).first()
        if obj is None:
            return Response({"detail": "Archivo no encontrado."}, status=404)
        # Best-effort: borra el blob cifrado en Mongo antes de la fila SQL.
        if obj.mongo_id:
            try:
                from apps.documentos.services import mongo_storage
                mongo_storage.borrar(obj.mongo_id)
            except Exception:
                logger.exception("No se pudo borrar el blob Mongo %s", obj.mongo_id)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


from django.http import Http404, HttpResponse  # noqa: E402
from apps.login.decorators import jwt_or_session_required, modulo_required  # noqa: E402


@jwt_or_session_required
@modulo_required("festivales")
def festival_archivo_descargar(request, pk: int):
    """Descifra y entrega una evidencia desde Mongo (descarga autenticada).

    Acepta Bearer JWT (SPA, fetch blob) o sesión. El binario nunca se
    persiste en disco del servidor; se descifra al vuelo por petición.
    """
    obj = FestivalArchivo.objects.filter(pk=pk).first()
    if obj is None or not obj.mongo_id:
        raise Http404("Evidencia no encontrada.")
    from apps.documentos.services import mongo_storage
    try:
        plaintext, mime = mongo_storage.leer(obj.mongo_id)
    except Exception:
        logger.exception("Error leyendo evidencia %s desde Mongo", obj.mongo_id)
        raise Http404("No se pudo recuperar el archivo.")
    response = HttpResponse(plaintext, content_type=mime or "application/octet-stream")
    nombre = obj.nombre_archivo or f"festival_archivo_{pk}"
    disp = "inline" if obj.es_imagen else "attachment"
    response["Content-Disposition"] = f'{disp}; filename="{nombre}"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
