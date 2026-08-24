"""El plan de pago de un contrato: la fuente oficial primero, la captura después.

DOS FUENTES, UNA LECTURA. `secop_plan_pago` es el espejo oficial (36.210 filas,
4.887 contratos) y `contrato_plan_pago` es lo que captura el área cuando SECOP
no publica nada — 5 de nuestros 25 contratos, entre ellos el de Educación.

    hay plan en SECOP  →  se muestra el de SECOP, y NO se puede capturar
    no hay             →  el área lo captura

Ese orden es la precedencia de fuentes (Constitución II) aplicada a una tabla
en vez de a un campo. Y es la razón por la que la tabla capturada NO replica a
SECOP: dos copias del mismo plan se separan en la primera corrida del cron.

`secuencia = 0` al leer SECOP porque la pareja (contrato, pago) NO es única:
cuatro pagos vienen dos veces con distinto aprobador. Sólo el primero suma.
"""
from __future__ import annotations

from decimal import Decimal


def _num(v):
    return float(v) if v is not None else None


def plan_de_pago(contrato) -> dict:
    """El plan de UN contrato, venga de donde venga.

    Devuelve `fuente`, las `filas` y los totales. `fuente` es lo que decide si
    la pantalla ofrece capturar: sobre un plan oficial no se escribe.
    """
    from django.db import connection

    from apps.presupuesto.models.plan_pago import ContratoPlanPago

    filas, fuente = [], None

    # ── 1. la oficial ──
    if contrato.contrato_numero and contrato.contrato_vigencia:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id_de_pago, estado, fecha_de_emision, valor_a_pagar, valor_neto
                FROM secop_plan_pago
                WHERE ref_numero = %s AND ref_vigencia = %s AND secuencia = 0
                ORDER BY fecha_de_emision NULLS LAST, id
            """, [contrato.contrato_numero, contrato.contrato_vigencia])
            for i, (idpago, estado, fecha, a_pagar, neto) in enumerate(cur.fetchall(), 1):
                filas.append({
                    "orden": i,
                    "periodo": (f"Pago {idpago}" if idpago else f"Pago {i}"),
                    "fecha": fecha.isoformat() if fecha else None,
                    "programado": _num(a_pagar),
                    "pagado": _num(neto),
                    "estado": estado,
                    "editable": False,
                })
        if filas:
            fuente = "SECOP"

    # ── 2. la capturada, sólo si la oficial no trae nada ──
    if not filas:
        for f in ContratoPlanPago.objects.filter(contrato_id=contrato.id).order_by("orden"):
            filas.append({
                "id": f.id,
                "orden": f.orden,
                "periodo": f.periodo,
                "fecha": f.fecha_programada.isoformat() if f.fecha_programada else None,
                "programado": _num(f.programado),
                "pagado": _num(f.pagado),
                "observacion": f.observacion,
                "editable": True,
            })
        if filas:
            fuente = "MANUAL"

    # Los totales ignoran los NULL a propósito: sumar «no se sabe» como cero
    # daría un total que parece medido y no lo es.
    return {
        "fuente": fuente,
        "editable": fuente != "SECOP",
        "filas": filas,
        "n": len(filas),
        "programado": sum((f["programado"] or 0) for f in filas) or None,
        "pagado": sum((f["pagado"] or 0) for f in filas) or None,
    }


def guardar_plan(contrato, filas, usuario):
    """Reemplaza el plan capturado de un contrato por el que llega.

    Reemplazo completo y no fila por fila: el área edita el plan como una
    tabla, y un `PUT` del conjunto evita el baile de altas, bajas y
    reordenamientos que haría falta para lo mismo con tres endpoints.

    Valida antes de escribir nada. Devuelve `(filas_guardadas, error)`.
    """
    from django.db import transaction

    from apps.presupuesto.models.plan_pago import ContratoPlanPago

    if not isinstance(filas, list):
        return None, "El plan debe ser una lista de períodos."
    if len(filas) > 120:
        # Un plan de más de 120 períodos no es un plan: es un error de carga.
        return None, "Un plan de pago no puede tener más de 120 períodos."

    limpias, vistos = [], set()
    for i, f in enumerate(filas, 1):
        if not isinstance(f, dict):
            return None, f"El período {i} no tiene el formato esperado."
        periodo = (f.get("periodo") or "").strip()
        if not periodo:
            return None, f"El período {i} necesita un nombre (mes, hito o etapa)."
        if len(periodo) > 80:
            return None, f"El nombre del período {i} es demasiado largo."

        orden = f.get("orden", i)
        try:
            orden = int(orden)
        except (TypeError, ValueError):
            return None, f"El orden del período {i} no es un número."
        if orden in vistos:
            return None, f"Hay dos períodos con el orden {orden}."
        vistos.add(orden)

        def dec(clave):
            v = f.get(clave)
            if v in (None, ""):
                return None      # «no se sabe» — distinto de cero
            try:
                d = Decimal(str(v))
            except Exception:    # noqa: BLE001
                raise ValueError(f"El {clave} del período {i} no es un número.")
            if d < 0:
                raise ValueError(f"El {clave} del período {i} no puede ser negativo.")
            return d

        try:
            programado, pagado = dec("programado"), dec("pagado")
        except ValueError as e:
            return None, str(e)

        fecha = (f.get("fecha") or f.get("fecha_programada") or None) or None

        limpias.append(ContratoPlanPago(
            contrato_id=contrato.id, orden=orden, periodo=periodo,
            fecha_programada=fecha, programado=programado, pagado=pagado,
            observacion=(f.get("observacion") or None), usuario_id=usuario.id))

    with transaction.atomic():
        ContratoPlanPago.objects.filter(contrato_id=contrato.id).delete()
        ContratoPlanPago.objects.bulk_create(limpias)

    return len(limpias), None
