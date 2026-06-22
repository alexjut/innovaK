"""API DRF del módulo Festivales (interno, autenticado).

Gating: módulo `festivales`. CRUD de la cabecera de festival + catálogos.
La galería/aforo/jurados/evaluación/publicación llegan en PR-2..PR-5.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission

from apps.festivales.models import Festival, TipoFestival
from apps.festivales.api.serializers import (
    FestivalDetailSerializer,
    FestivalSerializer,
    TipoFestivalSerializer,
)

_PERMS = [ModuloRequiredPermission("festivales")]


class FestivalListCreateView(APIView):
    """GET lista (filtros vigencia/estado/tipo) · POST crea."""

    permission_classes = _PERMS

    def get(self, request):
        qs = Festival.objects.select_related("tipo_festival").all()
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

    def get(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        return Response(FestivalDetailSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        ser = FestivalSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self._obj(pk)
        if obj is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        if obj.eventos.exists():
            return Response(
                {"detail": "No se puede eliminar: el festival tiene actos (eventos) asociados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        return Response({
            "tipos_festival": TipoFestivalSerializer(tipos, many=True).data,
            "vigencias": list(vigencias),
            "estados": [{"value": v, "label": l} for v, l in Festival.ESTADOS],
            "upls": upls,
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
