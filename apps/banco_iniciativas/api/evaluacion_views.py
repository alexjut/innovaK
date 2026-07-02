"""Endpoints del motor de puntaje del Banco (PR-1). Organizador, gated por módulo.

PR-1 expone: recalcular el bloque AUTO de un lote (evento) y ver la evaluación
de una inscripción. El bloque comité (70) y ranking van en PR-2/PR-3.
"""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.banco_iniciativas.models import (
    BancoEvaluacionInscripcion,
    InscripcionBancoIniciativa,
)
from apps.banco_iniciativas.services.puntaje import (
    recalcular_lote,
    calcular_caracterizacion,
)

_PERMS = [ModuloRequiredPermission("banco_iniciativas")]


class RecalcularLoteView(APIView):
    """POST /banco-iniciativas/api/evaluacion/recalcular-lote/  {evento_id}
    Recalcula el AUTO de todas las inscripciones del evento. Idempotente."""
    permission_classes = _PERMS

    def post(self, request):
        evento_id = request.data.get("evento_id")
        if not evento_id:
            return Response({"detail": "evento_id es obligatorio."}, status=400)
        res = recalcular_lote(int(evento_id))
        return Response({"detail": f"Recalculadas {res['procesadas']} inscripciones.", **res})


class EvaluacionDetailView(APIView):
    """GET /banco-iniciativas/api/inscripciones/<id>/evaluacion/
    Evaluación de una inscripción: bloque AUTO (puntaje + desglose por criterio).
    Si no hay evaluación persistida, calcula el AUTO al vuelo (preview)."""
    permission_classes = _PERMS

    def get(self, request, inscripcion_id):
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=inscripcion_id)
        ev = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).first()
        if ev is not None:
            return Response({
                "inscripcion_id": insc.id,
                "estado": ev.estado,
                "rubrica_version": ev.rubrica_version,
                "puntaje_auto": float(ev.puntaje_auto or 0),
                "puntaje_comite": float(ev.puntaje_comite) if ev.puntaje_comite is not None else None,
                "bono_genero": float(ev.bono_genero or 0),
                "total": float(ev.total) if ev.total is not None else None,
                "auto_detalle": ev.auto_detalle,
                "n_evaluadores": ev.n_evaluadores,
                "persistida": True,
            })
        calc = calcular_caracterizacion(insc)
        return Response({
            "inscripcion_id": insc.id,
            "estado": "pendiente",
            "rubrica_version": calc["version"],
            "puntaje_auto": calc["puntaje"],
            "auto_detalle": calc["criterios"],
            "persistida": False,
        })
