"""Endpoints del motor de puntaje del Banco. Organizador, gated por módulo.

**Desde el 2026-08-10 el motor activo es la MATRIZ OFICIAL** (Documento Maestro
2026-07-29, 100 puntos, sin comité). Antes estos endpoints corrían
`services/puntaje.py` (65 automáticos + 35 de comité + 5 de bono): la matriz
oficial estaba programada y probada pero **no era la que calificaba**, así que
el ranking que veía el usuario no era el del documento vigente.

`services/puntaje.py` NO se borra: es la única forma de releer cómo se evaluó el
piloto de mayo. Sigue importado más abajo solo para eso.

El comité desapareció del modelo oficial, así que `ComiteEvaluarView` ya no
evalúa: responde 409 explicando por qué. Se conserva la ruta —en vez de
borrarla— para que un cliente viejo reciba el motivo y no un 404 mudo.
"""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.banco_iniciativas.models import (
    BancoEvaluacionInscripcion,
    InscripcionBancoIniciativa,
)
from apps.banco_iniciativas.services.matriz_oficial import (
    CUPOS_ADJUDICABLES,
    DECISIONES_DEPORTES,
    MATRIZ_VERSION,
    calcular_matriz_oficial,
)
from apps.banco_iniciativas.services.ranking_oficial import (
    adjudicada,
    detalle_oficial,
    asignar_ranking_evento,
    es_oficial,
    guardar_evaluacion_oficial,
    recalcular_lote_oficial,
)

_PERMS = [ModuloRequiredPermission("banco_iniciativas")]

#: Motivo del 409 del comité. Es texto de cara al usuario, no un detalle interno.
_MOTIVO_SIN_COMITE = (
    "La matriz oficial del Documento Maestro (2026-07-29) elimina el comité de "
    "evaluación: los 100 puntos se liquidan automáticamente. Este endpoint "
    "pertenecía al modelo anterior (65 automáticos + 35 de comité + 5 de bono) "
    "y ya no aplica."
)


def _cuenta_oficiales(evento_id):
    """Cuántas evaluaciones oficiales tiene el evento (denominador de los cupos)."""
    return BancoEvaluacionInscripcion.objects.filter(
        inscripcion__evento_id=evento_id,
        rubrica_version=MATRIZ_VERSION,
    ).count()


class RecalcularLoteView(APIView):
    """POST /banco-iniciativas/api/evaluacion/recalcular-lote/  {evento_id}
    Recalcula con la matriz oficial todas las inscripciones del evento y
    renumera el ranking. Idempotente."""
    permission_classes = _PERMS

    def post(self, request):
        evento_id = request.data.get("evento_id")
        if not evento_id:
            return Response({"detail": "evento_id es obligatorio."}, status=400)
        res = recalcular_lote_oficial(int(evento_id))
        return Response({
            "detail": f"Recalculadas {res['procesadas']} inscripciones con la matriz oficial.",
            "motor": "oficial",
            **res,
        })


class RankingView(APIView):
    """GET  /banco-iniciativas/api/evaluacion/ranking/?evento_id=<id>
    POST idem — renumera sin recalcular los puntajes.

    El orden de adjudicación del evento, con la posición, el tope presupuestal
    de cada una y si queda dentro de los cupos."""
    permission_classes = _PERMS

    def get(self, request):
        evento_id = request.query_params.get("evento_id")
        if not evento_id:
            return Response({"detail": "evento_id es obligatorio."}, status=400)
        evento_id = int(evento_id)

        evaluaciones = (BancoEvaluacionInscripcion.objects
                        .filter(inscripcion__evento_id=evento_id,
                                rubrica_version=MATRIZ_VERSION)
                        .select_related("inscripcion", "inscripcion__organizacion")
                        .order_by("ranking_pos"))
        total = evaluaciones.count()

        filas = [{
            "inscripcion_id": ev.inscripcion_id,
            "organizacion": getattr(ev.inscripcion.organizacion, "nombre", None),
            "ranking_pos": ev.ranking_pos,
            "total": float(ev.total or 0),
            "bloque1": detalle_oficial(ev).get("bloque1", {}).get("pts"),
            "bloque2": detalle_oficial(ev).get("bloque2", {}).get("pts"),
            "tope_presupuestal": detalle_oficial(ev).get("tope_presupuestal"),
            "formulario_anterior": detalle_oficial(ev).get("formulario_anterior", False),
            "adjudicada": adjudicada(ev, total),
        } for ev in evaluaciones]

        return Response({
            "motor": "oficial",
            "version": MATRIZ_VERSION,
            "evento_id": evento_id,
            "cupos": CUPOS_ADJUDICABLES,
            "postuladas": total,
            "cupos_insuficientes": total < CUPOS_ADJUDICABLES,
            "decisiones_pendientes": DECISIONES_DEPORTES,
            "ranking": filas,
        })

    def post(self, request):
        evento_id = request.data.get("evento_id")
        if not evento_id:
            return Response({"detail": "evento_id es obligatorio."}, status=400)
        res = asignar_ranking_evento(int(evento_id))
        return Response({"detail": "Ranking renumerado.", "motor": "oficial", **res})


class EvaluacionDetailView(APIView):
    """GET   /banco-iniciativas/api/inscripciones/<id>/evaluacion/
    Evaluación de una inscripción con el desglose de los 12 criterios.
    Si no hay evaluación persistida, calcula al vuelo (preview, no escribe).

    POST  la calcula Y la persiste."""
    permission_classes = _PERMS

    def get(self, request, inscripcion_id):
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=inscripcion_id)
        ev = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).first()

        # Una fila del motor viejo NO se sirve como si fuera oficial: se
        # recalcula al vuelo con la matriz vigente y se avisa que lo guardado
        # quedó atrás. Persistirlo es un POST explícito, no un efecto de leer.
        if ev is not None and not es_oficial(ev):
            calc = calcular_matriz_oficial(insc)
            return Response({
                **self._cuerpo(insc, calc, ev=None),
                "persistida": False,
                "evaluacion_previa_obsoleta": {
                    "rubrica_version": ev.rubrica_version,
                    "total": float(ev.total) if ev.total is not None else None,
                    "nota": "Calculada con el modelo anterior (105 puntos, con "
                            "comité). Se conserva como evidencia del piloto; "
                            "recalcule para dejar la oficial en firme.",
                },
            })

        if ev is not None:
            return Response({**self._cuerpo(insc, detalle_oficial(ev), ev=ev),
                             "persistida": True})

        return Response({**self._cuerpo(insc, calcular_matriz_oficial(insc), ev=None),
                         "persistida": False})

    def post(self, request, inscripcion_id):
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=inscripcion_id)
        ev = guardar_evaluacion_oficial(insc)
        asignar_ranking_evento(insc.evento_id)
        ev.refresh_from_db()
        return Response({**self._cuerpo(insc, detalle_oficial(ev), ev=ev),
                         "persistida": True,
                         "detail": "Evaluación oficial calculada y guardada."})

    def _cuerpo(self, insc, calc, ev):
        """Respuesta común. Conserva las claves del motor viejo que el frontend
        ya leía (`puntaje_auto`, `total`, `auto_detalle`) para no romper nada."""
        total = calc.get("total", 0)
        cuerpo = {
            "inscripcion_id": insc.id,
            "motor": "oficial",
            "rubrica_version": MATRIZ_VERSION,
            "estado": ev.estado if ev else "pendiente",
            # Compatibilidad con el contrato anterior.
            "puntaje_auto": total,
            "puntaje_comite": None,
            "bono_genero": 0,
            "total": total,
            "auto_detalle": calc,
            # Lo propio de la matriz oficial.
            "total_max": calc.get("total_max"),
            "bloque1": calc.get("bloque1"),
            "bloque2": calc.get("bloque2"),
            "criterios": calc.get("criterios", []),
            "tope_presupuestal": calc.get("tope_presupuestal"),
            "regla_tope_presupuestal": calc.get("regla_tope_presupuestal"),
            "formulario_anterior": calc.get("formulario_anterior", False),
            "decisiones_pendientes": calc.get("decisiones_pendientes", DECISIONES_DEPORTES),
            "advertencias": calc.get("advertencias", []),
            "comite": None,
            "motivo_sin_comite": _MOTIVO_SIN_COMITE,
        }
        if ev is not None:
            total_oficiales = _cuenta_oficiales(insc.evento_id)
            cuerpo["ranking_pos"] = ev.ranking_pos
            cuerpo["cupos"] = CUPOS_ADJUDICABLES
            cuerpo["postuladas"] = total_oficiales
            cuerpo["adjudicada"] = adjudicada(ev, total_oficiales)
        return cuerpo


class ComiteEvaluarView(APIView):
    """Retirada por el Documento Maestro. Responde 409 con el motivo.

    La ruta sobrevive a propósito: un 404 dejaría al cliente viejo adivinando.
    """
    permission_classes = _PERMS

    def get(self, request, inscripcion_id):
        return self._retirada()

    def post(self, request, inscripcion_id):
        return self._retirada()

    def _retirada(self):
        return Response({
            "detail": _MOTIVO_SIN_COMITE,
            "motor": "oficial",
            "rubrica_version": MATRIZ_VERSION,
        }, status=409)
