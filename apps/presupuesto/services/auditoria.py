"""Registrar un cambio de dato institucional.

UNA función. La usan todos los flujos de captura, y por eso importa que sea
difícil de usar mal:

    registrar_cambio(
        usuario=request.user,
        entidad="contrato", entidad_id=105, campo="etapa",
        valor_anterior=None, valor_nuevo="2",
        contrato_id=105, proyecto_id=2805, subgrupo_id=8,
        fuente=AuditoriaDato.MANUAL,
    )

Tres decisiones que tienen razón de ser:

**El contexto se resuelve solo si no se lo dan.** Pasar `contrato_id` y que el
servicio deduzca proyecto y subgrupo evita que cada llamador repita —y
eventualmente equivoque— la misma consulta.

**Nunca lanza.** Si la auditoría falla, el dato ya se guardó: reventar dejaría
al usuario viendo un error por algo que sí funcionó. Se registra en el log y
sigue. Lo contrario —perder el dato por no poder auditarlo— es peor.

**No se registra un cambio que no cambió nada.** Si el valor entra igual al que
ya estaba, no hay fila. Una auditoría llena de ruido no se lee, y una que no se
lee no sirve.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _texto(v):
    """A texto, cuidando el cero.

    `None` significa «estaba vacío». `0` significa cero, y tiene que llegar
    como la cadena "0" — si se convirtiera a None, la auditoría diría que el
    campo estaba vacío cuando en realidad valía cero.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return "sí" if v else "no"
    return str(v)


def _contexto_de_contrato(contrato_id):
    """Deduce proyecto y subgrupo desde el contrato, por las dos vías."""
    from apps.presupuesto.models.core import ContratoProyecto, Proyecto
    from apps.presupuesto.models.sql import ContratoActividadPlan

    pid = (ContratoProyecto.objects.filter(contrato_id=contrato_id)
           .values_list("proyecto_id", flat=True).first())
    if pid is None:
        pid = (ContratoActividadPlan.objects
               .filter(contrato_id=contrato_id, activo=True)
               .values_list("actividad_plan__proyecto_id", flat=True).first())
    sid = (Proyecto.objects.filter(id=pid).values_list("subgrupo_id", flat=True).first()
           if pid else None)
    return pid, sid


def registrar_cambio(*, usuario, entidad: str, entidad_id: int, campo: str,
                     valor_anterior=None, valor_nuevo=None,
                     contrato_id=None, proyecto_id=None, subgrupo_id=None,
                     fuente: str | None = None, observacion: str | None = None):
    """Deja constancia de un cambio. Devuelve la fila creada, o `None`.

    `None` significa una de dos: el valor no cambió, o la auditoría falló (y
    quedó en el log). Nunca lanza.
    """
    from apps.presupuesto.models.auditoria import AuditoriaDato

    try:
        antes, despues = _texto(valor_anterior), _texto(valor_nuevo)
        if antes == despues:
            return None   # no cambió nada: no hay nada que auditar

        if contrato_id is not None and (proyecto_id is None or subgrupo_id is None):
            pid, sid = _contexto_de_contrato(contrato_id)
            proyecto_id = proyecto_id if proyecto_id is not None else pid
            subgrupo_id = subgrupo_id if subgrupo_id is not None else sid

        return AuditoriaDato.objects.create(
            usuario_id=getattr(usuario, "id", None) or 0,
            usuario_nombre=(getattr(usuario, "username", None)
                            or getattr(usuario, "get_username", lambda: None)()
                            or None),
            entidad=entidad, entidad_id=entidad_id, campo=campo,
            proyecto_id=proyecto_id, contrato_id=contrato_id, subgrupo_id=subgrupo_id,
            valor_anterior=antes, valor_nuevo=despues,
            fuente=fuente or AuditoriaDato.MANUAL,
            observacion=observacion,
        )
    except Exception:
        # A propósito: el dato ya se guardó. Reventar acá le mostraría un error
        # al usuario por algo que sí funcionó, y encima perdería el cambio si
        # la vista hace rollback de la transacción.
        logger.exception(
            "No se pudo auditar %s#%s.%s (usuario=%s). El dato SÍ se guardó.",
            entidad, entidad_id, campo, getattr(usuario, "id", "?"))
        return None


def historial(entidad: str, entidad_id: int, limite: int = 50):
    """Los últimos cambios de una entidad, del más reciente al más viejo."""
    from apps.presupuesto.models.auditoria import AuditoriaDato
    return list(AuditoriaDato.objects
                .filter(entidad=entidad, entidad_id=entidad_id)[:limite])
