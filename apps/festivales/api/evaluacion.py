"""API de lineup + jurados + criterios + evaluación + ranking (PR-E).

Gating módulo `festivales`. El funcionario transcribe las calificaciones.
Consolidado = promedio ponderado por peso del criterio. La evaluación se
cierra cuando el festival pasa a `estado='cerrado'`.
"""
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.festivales.models import (
    Festival, FestivalArtista, FestivalCriterio, FestivalEvaluacion, FestivalJurado,
)

_PERMS = [ModuloRequiredPermission("festivales")]


# ── Serializers ───────────────────────────────────────────────────────────

class ArtistaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    dia_fecha = serializers.DateField(source="festival_dia.fecha", read_only=True, default=None)

    class Meta:
        model = FestivalArtista
        fields = ["id", "festival", "festival_dia", "dia_fecha", "nombre", "tipo",
                  "tipo_display", "persona_id", "organizacion_id", "descripcion",
                  "orden", "created_at"]
        read_only_fields = ["id", "festival", "created_at"]


class JuradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FestivalJurado
        fields = ["id", "festival", "nombre", "persona_id", "perfil", "created_at"]
        read_only_fields = ["id", "festival", "created_at"]


class CriterioSerializer(serializers.ModelSerializer):
    class Meta:
        model = FestivalCriterio
        fields = ["id", "festival", "nombre", "peso", "orden", "created_at"]
        read_only_fields = ["id", "festival", "created_at"]


# ── Helpers de listado-bajo-festival ───────────────────────────────────────

class _BajoFestivalListCreate(APIView):
    """GET lista bajo un festival · POST crea (festival viene en la URL)."""
    permission_classes = _PERMS
    modelo = None
    serializer = None

    def get(self, request, fid):
        if not Festival.objects.filter(pk=fid).exists():
            return Response({"detail": "Festival no encontrado."}, status=404)
        qs = self.modelo.objects.filter(festival_id=fid)
        return Response(self.serializer(qs, many=True).data)

    def post(self, request, fid):
        festival = Festival.objects.filter(pk=fid).first()
        if festival is None:
            return Response({"detail": "Festival no encontrado."}, status=404)
        ser = self.serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(festival=festival)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class _BajoFestivalDetail(APIView):
    """PATCH edita · DELETE elimina un hijo del festival."""
    permission_classes = _PERMS
    modelo = None
    serializer = None
    permite_patch = True

    def patch(self, request, pk):
        if not self.permite_patch:
            return Response(status=405)
        obj = self.modelo.objects.filter(pk=pk).first()
        if obj is None:
            return Response({"detail": "No encontrado."}, status=404)
        ser = self.serializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj = self.modelo.objects.filter(pk=pk).first()
        if obj is None:
            return Response({"detail": "No encontrado."}, status=404)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArtistaListCreateView(_BajoFestivalListCreate):
    modelo = FestivalArtista
    serializer = ArtistaSerializer


class ArtistaDetailView(_BajoFestivalDetail):
    modelo = FestivalArtista
    serializer = ArtistaSerializer


class JuradoListCreateView(_BajoFestivalListCreate):
    modelo = FestivalJurado
    serializer = JuradoSerializer


class JuradoDetailView(_BajoFestivalDetail):
    modelo = FestivalJurado
    serializer = JuradoSerializer
    permite_patch = False


class CriterioListCreateView(_BajoFestivalListCreate):
    modelo = FestivalCriterio
    serializer = CriterioSerializer


class CriterioDetailView(_BajoFestivalDetail):
    modelo = FestivalCriterio
    serializer = CriterioSerializer


# ── Evaluación (upsert) ─────────────────────────────────────────────────────

class EvaluacionUpsertView(APIView):
    """`POST /festivales/api/evaluaciones/` — transcribe un puntaje (upsert).

    Body: artista_id, jurado_id, criterio_id, puntaje, observacion?. Bloquea
    si el festival ya está cerrado.
    """
    permission_classes = _PERMS

    def post(self, request):
        try:
            artista_id = int(request.data["artista_id"])
            jurado_id = int(request.data["jurado_id"])
            criterio_id = int(request.data["criterio_id"])
            puntaje = float(request.data["puntaje"])
        except (KeyError, TypeError, ValueError):
            return Response({"detail": "Faltan artista_id, jurado_id, criterio_id o puntaje válidos."},
                            status=status.HTTP_400_BAD_REQUEST)

        artista = FestivalArtista.objects.select_related("festival").filter(pk=artista_id).first()
        if artista is None:
            return Response({"detail": "Artista no encontrado."}, status=404)
        if artista.festival.estado == Festival.CERRADO:
            return Response({"detail": "El festival está cerrado; la evaluación no se puede modificar."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Jurado y criterio deben ser del mismo festival.
        if not FestivalJurado.objects.filter(pk=jurado_id, festival_id=artista.festival_id).exists():
            return Response({"detail": "Jurado no pertenece al festival."}, status=status.HTTP_400_BAD_REQUEST)
        if not FestivalCriterio.objects.filter(pk=criterio_id, festival_id=artista.festival_id).exists():
            return Response({"detail": "Criterio no pertenece al festival."}, status=status.HTTP_400_BAD_REQUEST)

        obj, _ = FestivalEvaluacion.objects.update_or_create(
            festival_artista_id=artista_id,
            festival_jurado_id=jurado_id,
            festival_criterio_id=criterio_id,
            defaults={"puntaje": puntaje,
                      "observacion": (request.data.get("observacion") or "").strip() or None},
        )
        return Response({"id": obj.id, "puntaje": float(obj.puntaje)},
                        status=status.HTTP_200_OK)


class RankingView(APIView):
    """`GET /festivales/api/festivales/<fid>/ranking/` — planilla + consolidado.

    Consolidado por artista = promedio (entre jurados) del promedio ponderado
    por peso de los criterios. Devuelve también la planilla (artistas,
    jurados, criterios y evaluaciones existentes) para la UI.
    """
    permission_classes = _PERMS

    def get(self, request, fid):
        festival = Festival.objects.filter(pk=fid).first()
        if festival is None:
            return Response({"detail": "Festival no encontrado."}, status=404)

        artistas = list(FestivalArtista.objects.filter(festival_id=fid))
        jurados = list(FestivalJurado.objects.filter(festival_id=fid))
        criterios = list(FestivalCriterio.objects.filter(festival_id=fid))
        peso = {c.id: float(c.peso or 0) for c in criterios}

        evals = FestivalEvaluacion.objects.filter(festival_artista__festival_id=fid)
        # mapa[(artista, jurado, criterio)] = puntaje
        mapa = {}
        for e in evals:
            mapa[(e.festival_artista_id, e.festival_jurado_id, e.festival_criterio_id)] = float(e.puntaje)

        ranking = []
        for a in artistas:
            puntajes_jurado = []
            for j in jurados:
                num = den = 0.0
                for c in criterios:
                    p = mapa.get((a.id, j.id, c.id))
                    if p is not None:
                        num += p * peso.get(c.id, 0)
                        den += peso.get(c.id, 0)
                if den > 0:
                    puntajes_jurado.append(num / den)
            consolidado = round(sum(puntajes_jurado) / len(puntajes_jurado), 2) if puntajes_jurado else None
            ranking.append({
                "artista_id": a.id, "nombre": a.nombre, "tipo": a.get_tipo_display(),
                "n_jurados_calificaron": len(puntajes_jurado),
                "consolidado": consolidado,
            })

        # Ordena por consolidado desc (None al final) y asigna posición.
        ranking.sort(key=lambda r: (r["consolidado"] is None, -(r["consolidado"] or 0)))
        for i, r in enumerate(ranking, start=1):
            r["posicion"] = i if r["consolidado"] is not None else None

        return Response({
            "festival_id": fid,
            "cerrado": festival.estado == Festival.CERRADO,
            "artistas": ArtistaSerializer(artistas, many=True).data,
            "jurados": JuradoSerializer(jurados, many=True).data,
            "criterios": CriterioSerializer(criterios, many=True).data,
            "evaluaciones": [
                {"artista_id": e.festival_artista_id, "jurado_id": e.festival_jurado_id,
                 "criterio_id": e.festival_criterio_id, "puntaje": float(e.puntaje)}
                for e in evals
            ],
            "ranking": ranking,
        })
