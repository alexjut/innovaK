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

#: Por qué la cobertura del Plan es baja, dicho en la propia API. No es un
#: defecto del dato publicado: es una vinculación que carga el área a mano en
#: la intranet y que hoy existe para una fracción de los contratos.
_DEPENDE_CARGUE = (
    "Cargue manual en la intranet (tabla `contrato_actividad_plan`). No es un "
    "dato que SECOP publique: lo registra el área al enganchar el contrato con "
    "la actividad del Plan. Una cobertura baja acá significa que falta ese "
    "cargue, no que el contrato esté incompleto. NO lo declare obligatorio en "
    "su modelo: hoy bloquearía la mayoría de las cargas."
)


def _cobertura_periodos() -> dict:
    """Cuántos períodos de suspensión se pueden armar, y cuánto concuerdan.

    El contraste con `secop_contrato.estado_contrato` es lo que convierte esto
    en una medición y no en una afirmación: son dos caminos independientes —uno
    derivado de actos, el otro un campo publicado— y coinciden en 106 de 116.
    """
    from apps.publico.services import suspensiones as _s
    with connection.cursor() as cur:
        cur.execute("SELECT DISTINCT id_contrato FROM secop_suspension")
        ids = [r[0] for r in cur.fetchall()]
        cur.execute("""SELECT COUNT(*) FROM secop_contrato
                       WHERE lower(trim(estado_contrato)) = 'suspendido'""")
        susp_secop = int(cur.fetchone()[0] or 0)
    if not ids:
        return {"contratos_con_actos": 0, "periodos_cerrados": 0}
    res = _s.periodos(ids)
    cerrados = sum(len(v["periodos"]) for v in res.values())
    abiertas = sum(1 for v in res.values() if v["abierta"])
    discrepan = sum(1 for v in res.values() if v["discrepancia"])
    return {
        "contratos_con_actos": len(res),
        "periodos_cerrados": cerrados,
        "contratos_con_periodo_cerrado":
            sum(1 for v in res.values() if v["periodos"]),
        "cadenas_abiertas": abiertas,
        "reanudaciones_sin_suspension":
            sum(v["reanudaciones_sin_suspension"] for v in res.values()),
        "contraste_con_estado_secop": {
            "secop_dice_suspendido": susp_secop,
            "nuestra_cadena_queda_abierta": abiertas,
            "discrepancias_declaradas": discrepan,
            "nota": ("Las discrepancias no se resuelven, se publican. En los "
                     "casos medidos el último día trae una suspensión Y una "
                     "reanudación, y el orden dentro del mismo día no está en "
                     "el dato."),
        },
        "metodo": _s.METODO,
        "advertencia": _s.MOTIVO_DIAS_ENTRE_ACTOS,
    }


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

        # LA INTERSECCIÓN CON EL ESPEJO, no los ids de la tabla puente. Es el
        # mismo error que ya había dado una cobertura del 160 % en el plan de
        # pagos, repetido acá y sin delatarse: `contrato_actividad_plan.
        # contrato_id` apunta al `contrato` INTERNO, no a `secop_contrato`, así
        # que contar sus ids distintos y dividirlos entre los 3.189 del espejo
        # mezcla dos universos. Coincidía por casualidad —5 y 5— y por eso pasó
        # un mes sin que nadie lo viera; lo encontró el equipo que consume la
        # API al preguntar por qué su cobertura no cuadraba con la nuestra.
        _EN_PLAN = """
            FROM secop_contrato s
            WHERE EXISTS (
                SELECT 1 FROM contrato ct
                JOIN contrato_actividad_plan cap ON cap.contrato_id = ct.id
                -- El proyecto NO está en `contrato`: se llega por la actividad
                -- del plan (`actividad_plan.proyecto_id`). `contrato` tiene un
                -- `proyecto_codigo` denormalizado que no es la vía de la
                -- cadena. Se comprobó contra information_schema antes de
                -- escribirlo: `contrato.proyecto_id` no existe.
                LEFT JOIN actividad_plan ap ON ap.id = cap.actividad_plan_id
                WHERE cap.activo
                  AND upper(trim(s.referencia_contrato)) ~
                      ('(^|[^0-9])' || ct.contrato_numero ||
                       '[^0-9]+' || ct.contrato_vigencia)
                  {extra}
            )"""
        cur.execute("SELECT COUNT(*) " + _EN_PLAN.format(extra=""))
        con_actividad = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(*) " + _EN_PLAN.format(
            extra="AND cap.meta_proyecto_id IS NOT NULL"))
        con_meta = int(cur.fetchone()[0] or 0)
        # Y el PROYECTO, que no se publicaba como cifra y es la que preguntaron.
        cur.execute("SELECT COUNT(*) " + _EN_PLAN.format(
            extra="AND ap.proyecto_id IS NOT NULL"))
        con_proyecto = int(cur.fetchone()[0] or 0)

        # Cuántas filas tocó la última corrida. Es el dato honesto de
        # frescura: decir «3.147 filas sin cambio desde el corte» sugiere un
        # dataset viejo cuando lo cierto es que la ingesta corrió hoy y solo 5
        # contratos habían cambiado.
        cur.execute("SELECT COUNT(*) FROM secop_contrato WHERE synced_at::date = %s::date",
                    [corte])
        tocadas = int(cur.fetchone()[0] or 0)

        # El eje suspensión/reanudación. Se mide en vivo porque la cifra es la
        # que justifica NO usar `modificacion.tipo`, y una cifra escrita a mano
        # se queda atrás sin avisar.
        cur.execute("SELECT to_regclass('public.secop_suspension') IS NOT NULL")
        hay_actos = bool(cur.fetchone()[0])
        eje = None
        if hay_actos:
            # Con un LEFT JOIN, un contrato con DOS actos en la misma
            # fecha DUPLICA la fila del par y la cuenta dos veces: daba 476
            # filas donde el servicio ve 432. El acto se busca con una
            # subconsulta que devuelve UNO, y en el mismo orden en que lo
            # elige `modificaciones.por_contrato`, para que las dos cifras no
            # puedan separarse.
            cur.execute("""
                WITH par AS (
                  SELECT id_contrato,
                         COALESCE(fecha_aprobacion, fecha_creacion) f,
                         tipo
                  FROM secop_modificacion
                  WHERE tipo IN ('SUSPENSIoN','REACTIVACIoN')),
                dobles AS (
                  SELECT id_contrato, f FROM par GROUP BY 1,2 HAVING COUNT(*) > 1),
                marcado AS (
                  SELECT p.tipo,
                         EXISTS (SELECT 1 FROM dobles d
                                  WHERE d.id_contrato = p.id_contrato
                                    AND d.f = p.f) ambigua,
                         (SELECT s.tipo_codigo FROM secop_suspension s
                           WHERE s.id_contrato = p.id_contrato
                             AND p.f IN (s.fecha_aprobacion, s.fecha_creacion)
                           ORDER BY COALESCE(s.fecha_aprobacion, s.fecha_creacion),
                                    s.id
                           LIMIT 1) oficial
                  FROM par p)
                SELECT COUNT(*),
                       COUNT(oficial) FILTER (WHERE NOT ambigua),
                       COUNT(*) FILTER (WHERE ambigua),
                       COUNT(*) FILTER (
                           WHERE oficial IS NOT NULL AND NOT ambigua
                             AND oficial <> CASE tipo WHEN 'SUSPENSIoN'
                                                      THEN 'SUSPENSION'
                                                      ELSE 'REANUDACION' END)
                FROM marcado""")
            n_par, n_cls, n_amb, n_inv = cur.fetchone()
            eje = {
                "filas_del_par": int(n_par or 0),
                "clasificadas": int(n_cls or 0),
                "ambiguas": int(n_amb or 0),
                "tipo_contradice_al_acto_oficial": int(n_inv or 0),
            }

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
            # Las tres del Plan llevan `depende_de` porque su cifra baja no es
            # un defecto de esta API: es un cargue que todavía no se hizo, y sin
            # decirlo se lee como si el dato estuviera roto.
            "con_proyecto_del_plan": {
                "n": con_proyecto, "pct": _pct(con_proyecto),
                "depende_de": _DEPENDE_CARGUE},
            "con_actividad_del_plan": {
                "n": con_actividad, "pct": _pct(con_actividad),
                "depende_de": _DEPENDE_CARGUE},
            "con_meta_del_plan": {
                "n": con_meta, "pct": _pct(con_meta),
                "depende_de": _DEPENDE_CARGUE},
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
        # Las dos convenciones de fecha de fin, que miden al revés. Lo
        # preguntaron porque sus dos campos difieren en un día y no es un
        # error: son dos datasets con convenciones opuestas.
        "convencion_fechas_fin": {
            "contrato.fechas.fin_actual": {
                "convencion": "INCLUSIVA — último día de ejecución.",
                "dataset": "jbjy-vk9h",
                "manda": True,
                "nota": ("Es la que gobierna el plazo: ya absorbe "
                         "`dias_adicionados`. Es la que va en un certificado."),
            },
            "modificacion.contrato_fecha_fin": {
                "convencion": "EXCLUSIVA — el día SIGUIENTE al último de ejecución.",
                "dataset": "u8cx-r425",
                "manda": False,
                "nota": ("Es una foto de UNA versión de la modificación y puede "
                         "quedarse atrás. Se publica además "
                         "`contrato_fecha_fin_inclusiva`, ya restada."),
            },
            "desfase_medido": ("+1 día en 88,2 % de los contratos con "
                               "modificación en firme, 0 en 7,9 %, negativo en "
                               "77 y por encima de +1 en 5."),
        },
        # El campo `tipo` del par suspensión/reactivación viene INVERTIDO en el
        # origen. Se declara acá, con la cifra en vivo, porque un consumidor que
        # filtre por `tipo` fecharía la suspensión el día del reinicio —y eso va
        # a un paz y salvo—. Es el mismo motivo por el que existe
        # `convencion_fechas_fin`: la trampa se publica, no se esconde.
        "eje_suspension": ({
            "regla": ("La clase `suspension`/`reanudacion` NO sale de "
                      "`modificacion.tipo`. Sale del dataset dedicado de "
                      "suspensiones y reanudaciones (u99c-7mfm), que trae dos "
                      "tipos limpios, y cada clase viaja con su campo "
                      "`clases_motivo` nombrando ese dataset."),
            "no_usar": "modificacion.tipo",
            "dataset": "u99c-7mfm",
            "medido": eje,
            "nota_ambiguas": ("Cuando un contrato tiene DOS modificaciones del "
                              "par en la MISMA fecha, el acto oficial no dice a "
                              "cuál corresponde: no se publica clase y "
                              "`clases_advertencia` lo dice. Elegir una sería "
                              "acertar la mitad de las veces."),
            "auditable_en": ("Cada clase trae `suspension_proposito_oficial`, "
                             "el texto del acto, para comprobarla a mano."),
            # La cobertura de los PERÍODOS se saca del propio servicio, no de
            # una consulta paralela: la primera versión de la medición de arriba
            # llevaba su propio SQL y publicó 476 donde el servicio veía 432.
            # Dos caminos al mismo número es una forma de que uno quede viejo.
            "periodos": _cobertura_periodos(),
        } if eje else {
            "regla": ("El eje suspensión/reanudación no se publica en este "
                      "despliegue: falta la tabla espejo del dataset dedicado."),
            "no_usar": "modificacion.tipo",
            "medido": None,
        }),
        # El compromiso de servicio. Está acá y no en un correo porque un
        # consumidor que alimenta documentos con efectos jurídicos tiene que
        # poder leerlo desde la misma API de la que depende.
        "compatibilidad": {
            "version": "v1",
            "politica": ("La v1 no quita ni renombra campos. Los campos nuevos "
                         "se agregan sin tocar los existentes."),
            "aviso_cambios_dias": 15,
            "campos_en_retiro": {
                "modificacion.tipo": ("Alias de `tipo_codigo` por un ciclo. "
                                      "Cablearse a `tipo_codigo`, que es "
                                      "estable frente a la grafía del origen."),
                "modificacion.proveedor_anterior": "Siempre null; usar `cedente`.",
                "modificacion.proveedor_nuevo": ("Siempre null; el contratista "
                                                 "nuevo está en "
                                                 "`contrato.proveedor`."),
            },
            "garantia_tecnica": ("La suite de pruebas del proyecto falla si un "
                                 "campo del contrato o de la modificación "
                                 "desaparece."),
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
