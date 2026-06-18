"""API DRF del módulo Festivales (interno, autenticado).

Gating: módulo `festivales`. CRUD de la cabecera de festival + catálogos.
La galería/aforo/jurados/evaluación/publicación llegan en PR-2..PR-5.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission

from apps.festivales.models import Festival, TipoFestival
from apps.festivales.api.serializers import (
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
        return Response(FestivalSerializer(obj).data)

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
        vigencias = sorted(
            Festival.objects.values_list("vigencia", flat=True).distinct(), reverse=True,
        )
        return Response({
            "tipos_festival": TipoFestivalSerializer(tipos, many=True).data,
            "vigencias": list(vigencias),
            "estados": [{"value": v, "label": l} for v, l in Festival.ESTADOS],
        })
