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
    guardar_caracterizacion,
    guardar_comite,
    COMITE_VALORES,
    INCLUSION_CODIGOS,
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
                # Comité BINARIO ya guardado → pre-carga del form del panel.
                "viabilidad_cumple": ev.viabilidad_cumple,
                "ambiental_cumple": ev.ambiental_cumple,
                "innovacion_cumple": ev.innovacion_cumple,
                "bono_mujeres": ev.bono_mujeres,
                "comite_observacion": ev.comite_observacion,
                "evaluador_id": ev.evaluador_id,
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


class ComiteEvaluarView(APIView):
    """POST /banco-iniciativas/api/inscripciones/<id>/evaluacion/comite/
    El evaluador (usuario actual) guarda sus puntajes de los criterios de comité
    + su voto de bono mujeres. Body: {criterios:{C6_viabilidad:.., ...}, bono:bool,
    observaciones:{codigo:texto}}. Idempotente por evaluador. Recalcula la cabecera."""
    permission_classes = _PERMS

    def get(self, request, inscripcion_id):
        """Contexto del panel: criterios de comité con su max + guías, y los
        chips de inclusión {4,5,6} que marcó la org (referencia, no puntúan auto)."""
        from apps.banco_iniciativas.models import (
            InscripcionBancoIniciativa, EnfoquePropuesta)
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=inscripcion_id)
        ep = set(insc.enfoques_propuesta.values_list("codigo", flat=True))
        ref = [{"codigo": e.codigo, "nombre": e.nombre}
               for e in EnfoquePropuesta.objects.filter(codigo__in=(ep & INCLUSION_CODIGOS))]
        return Response({
            "inscripcion_id": insc.id,
            # Comité BINARIO (sí/no): valor que otorga cada criterio si cumple.
            "criterios_comite": [{"codigo": k, "valor": v} for k, v in COMITE_VALORES.items()],
            "bono_disponible": bool(insc.enfoque_genero_mujer),   # pre-señal del form
            "inclusion_referencia": ref,                          # chips {4,5,6} marcados (ya auto)
        })

    def post(self, request, inscripcion_id):
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=inscripcion_id)
        ev = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).first()
        if ev is None:
            ev = guardar_caracterizacion(insc)   # asegura cabecera + auto
        d = request.data
        ev = guardar_comite(
            ev, request.user.id,
            viabilidad=bool(d.get("viabilidad")),
            ambiental=bool(d.get("ambiental")),
            innovacion=bool(d.get("innovacion")),
            bono=bool(d.get("bono")),
            observacion=d.get("observacion"),
        )
        return Response({
            "detail": "Evaluación registrada.",
            "puntaje_auto": float(ev.puntaje_auto or 0),
            "puntaje_comite": float(ev.puntaje_comite) if ev.puntaje_comite is not None else None,
            "bono_genero": float(ev.bono_genero or 0),
            "total": float(ev.total) if ev.total is not None else None,
            "estado": ev.estado,
        })
