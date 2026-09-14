"""De cuándo es el dato y qué tan completo está. Lo primero que pide quien consume.

Sin esto, un tercero no puede saber si la cifra que acaba de bajar es de hoy o
de hace un mes, ni si un campo vacío significa «no pasó» o «no lo tenemos».

## `synced_at` NO es la fecha de corte

Es la trampa de este dataset y por eso se calcula aparte. El upsert de la
ingesta solo toca `synced_at` cuando el hash de la fila CAMBIA
(`ingest_secop_contratos.py`), así que el campo dice «última vez que esta fila
se modificó», no «última vez que la verificamos». Medido: el máximo es de hoy,
pero 1.821 de las 3.152 filas siguen marcando julio. Un consumidor que leyera
`synced_at` concluiría que el dato tiene mes y medio.

Mientras no exista una tabla de corridas de sincronización, `corte` es el
MÁXIMO de `synced_at` —que sí corresponde a la última corrida que encontró
cambios— y se publica junto a `filas_sin_cambio_desde` para que el desfase
quede a la vista en vez de escondido.
"""
from __future__ import annotations

from django.db import connection


def metadatos() -> dict:
    with connection.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), MAX(synced_at), MIN(synced_at),
                   COALESCE(SUM(valor_contrato), 0),
                   COUNT(*) FILTER (WHERE valor_pagado = 0),
                   MIN(anio), MAX(anio)
            FROM secop_contrato
        """)
        (filas, corte, primer_sync, valor, pagado_cero, anio_min, anio_max) = cur.fetchone()

        # LA INTERSECCIÓN, no los ids del plan de pagos. `secop_plan_pago`
        # tiene 5.048 identificadores distintos y nuestro espejo 3.152: esa
        # tabla trae contratos que no son de este alcance. Contar sus ids daba
        # una cobertura del 160 %, que es la clase de cifra que delata el
        # error sola — si hubiera dado 95 % habría pasado desapercibida.
        cur.execute("""
            SELECT COUNT(*) FROM secop_contrato s
            WHERE EXISTS (SELECT 1 FROM secop_plan_pago p
                          WHERE p.id_del_contrato = s.id_contrato)
        """)
        con_plan = int(cur.fetchone()[0] or 0)

        cur.execute("""
            SELECT COUNT(*) FROM secop_contrato s
            WHERE EXISTS (SELECT 1 FROM contrato ct
                          WHERE upper(trim(s.referencia_contrato)) ~
                                ('(^|[^0-9])' || ct.contrato_numero ||
                                 '[^0-9]+' || ct.contrato_vigencia))
        """)
        con_expediente = int(cur.fetchone()[0] or 0)

        # CONTRATOS, no filas de la tabla puente: un contrato puede tener
        # varias actividades y el porcentaje tiene que ser comparable con los
        # de arriba, que están sobre los 3.152 del espejo.
        cur.execute("SELECT COUNT(DISTINCT contrato_id) FROM contrato_actividad_plan "
                    "WHERE activo")
        con_actividad = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(DISTINCT contrato_id) FROM contrato_actividad_plan "
                    "WHERE activo AND meta_proyecto_id IS NOT NULL")
        con_meta = int(cur.fetchone()[0] or 0)

        # Cuántas filas tocó la última corrida. Es el dato honesto de
        # frescura: decir «3.147 filas sin cambio desde el corte» sugiere un
        # dataset viejo cuando lo cierto es que la ingesta corrió hoy y solo 5
        # contratos habían cambiado.
        cur.execute("SELECT COUNT(*) FROM secop_contrato WHERE synced_at::date = %s::date",
                    [corte])
        tocadas = int(cur.fetchone()[0] or 0)

    filas = int(filas or 0)

    def _pct(n):
        return round(100.0 * n / filas, 2) if filas else None

    return {
        "nombre": "API de Contratación Pública — Alcaldía Local de Kennedy",
        "version": "v1",
        "estado": "beta",
        "corte": corte.isoformat() if corte else None,
        "corte_nota": (
            "Es el máximo de `synced_at`, que la ingesta solo actualiza cuando "
            "la fila CAMBIA. No es «última verificación de todo el dataset»: "
            "una fila que no cambió conserva la fecha de su último cambio, así "
            "que `cambio_mas_antiguo` puede ser de hace meses sin que el dato "
            "esté desactualizado."),
        "filas": filas,
        "filas_modificadas_en_la_ultima_corrida": tocadas,
        "cambio_mas_antiguo": primer_sync.isoformat() if primer_sync else None,
        "vigencias": {"desde": anio_min, "hasta": anio_max},
        "valor_total_contratado_cop": float(valor or 0),
        "alcance": ("Contratos adjudicados de la ALCALDIA LOCAL DE KENNEDY "
                    "(NIT 899999061) publicados en SECOP II."),
        "cobertura": {
            "con_plan_de_pagos": {"n": con_plan, "pct": _pct(con_plan)},
            "con_expediente_interno": {"n": con_expediente, "pct": _pct(con_expediente)},
            "con_actividad_del_plan": {"n": con_actividad, "pct": _pct(con_actividad)},
            "con_meta_del_plan": {"n": con_meta, "pct": _pct(con_meta)},
            "valor_pagado_no_publicable": {
                "n": int(pagado_cero or 0), "pct": _pct(int(pagado_cero or 0)),
                "motivo": ("SECOP reporta 0 y no distingue «no se giró» de «no "
                           "se reportó»: salen como null."),
            },
        },
        "identificador_estable": {
            "campo": "id_contrato",
            "ejemplo": "CO1.PCCNTR.7876249",
            "nota": ("Es el identificador de SECOP II, verificable en "
                     "datos.gov.co. NO use `referencia_contrato`: se repite."),
        },
        "convencion_sin_dato": {
            "regla": "Un dato ausente siempre es null, nunca 0.",
            "motivo": "Cada null viaja con su campo `<nombre>_motivo`.",
        },
        "fuente": "SECOP II — datos.gov.co, dataset jbjy-vk9h",
        "licencia": "CC-BY-4.0",
        "atribucion": "Fuente: Alcaldía Local de Kennedy a partir de SECOP II",
    }


def agregados() -> dict:
    """Totales por año, estado y modalidad. Lo que casi todos piden primero."""
    with connection.cursor() as cur:
        def _grupo(col):
            cur.execute(
                f"SELECT {col}, COUNT(*), COALESCE(SUM(valor_contrato), 0) "
                f"FROM secop_contrato GROUP BY 1 ORDER BY 2 DESC")
            return [{"clave": k, "contratos": int(n), "valor": float(v or 0)}
                    for k, n, v in cur.fetchall()]

        return {
            "por_anio": _grupo("anio"),
            "por_estado": _grupo("estado_contrato"),
            "por_modalidad": _grupo("modalidad"),
            "por_tipo": _grupo("tipo_contrato"),
        }
