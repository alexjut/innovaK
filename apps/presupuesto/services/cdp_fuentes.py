"""Los CDP del Fondo, leídos de BogData y contrastados con innovaK.

QUÉ ARREGLA
-----------
La pantalla de CDP mostraba **cinco filas**, y cuatro eran cáscaras: sin
número, sin fecha y sin valor, creadas solo para poder colgar un contrato. La
quinta era un CDP real. Encima la tabla pedía una columna `proyecto_nombre`
que el endpoint nunca mandó, así que la columna Proyecto salía vacía siempre.

Los CDP de verdad son **2.173** y están en BogData, que es quien los expide.
Medido sobre el corte del 7 de septiembre de 2026.

    CDP en BogData ............. 2.173, ejercicio 2026
    registrados en innovaK .....     5, cuatro de ellos sin número
    con proyecto identificado ..   568 de 2.173

LA CADENA, EN SU ORDEN (doctrina de Alex, 2026-09-11)
------------------------------------------------------

    Apropiación → CDP → proceso contractual → Contrato → CRP
                → ejecución → obligación → giro/pago

**El CRP va DESPUÉS del contrato**, no antes: el CDP reserva, el contrato se
firma contra esa reserva y solo entonces el CRP compromete definitivamente la
apropiación. En los FDL de Bogotá se expide tras la firma y antes del acta de
inicio.

**El CRP NO es plata pagada.** Comprometido, ejecutado, obligado y girado son
cuatro cifras distintas y normalmente lo son. Por eso acá el `valor_neto` se
publica rotulado «comprometido» y nunca como gasto.

**Y la relación no es 1 a 1**, medido en esta base: 248 CDP tienen más de un
CRP —uno llega a 36— y 172 compromisos se financian desde más de un CDP, uno
desde 13. Nada de lo que se construya encima puede suponer
`1 CDP = 1 CRP = 1 contrato`.

**Que el CDP sea mayor que el contrato es normal**, no un descuadre: el
sobrante queda sin comprometer y se libera por el procedimiento presupuestal.
Por eso la columna se llama «libre» y no «diferencia».

HASTA DÓNDE LLEGA EL ARCHIVO, Y DÓNDE SE CORTA
-----------------------------------------------
De los ocho eslabones, este archivo cubre hasta el séptimo a medias:

    valor_crp          $264.234.015.563   expedido
    anulaciones        $ 37.489.033.424
    valor_neto         $226.744.982.139   COMPROMETIDO (crp − anulaciones)
    autorizacion_giro  $126.648.571.200   giro AUTORIZADO
    com_sin_aut_giro   $100.096.410.939   comprometido sin autorizar

**No hay columna de obligación**, y la autorización de giro es la autorización,
no el pago hecho. Los dos últimos eslabones no vienen y no se inventan: la
pantalla los muestra como lo que son, sin dato.

QUIÉN MANDA PARA CADA DATO
--------------------------
    el CDP existe y con qué número ...... BogData
    cuánto se comprometió contra él ..... BogData  (Σ valor_neto de sus CRP)
    cuánto se giró ...................... BogData  (Σ autorizacion_giro)
    por cuánto se expidió ............... innovaK  (lo que alguien registró)
    a qué contrato del Plan sirve ....... innovaK

EL SALDO SOLO EXISTE CUANDO ESTÁN LAS DOS FUENTES, y ese es el punto de esta
pantalla. **El archivo del CRP no trae el valor del CDP**: trae lo que se
comprometió contra él. Así que «cuánto queda libre» no se puede calcular desde
BogData sola, ni desde innovaK sola. Con las dos, sí:

    CDP 1486 ... expedido $52.000.000 (innovaK)
                 comprometido $2.678.400 (BogData)
                 libre $49.321.600

Y por eso mismo **comprometido no se compara contra expedido como si fueran la
misma cifra**: que un CDP de $52 M tenga $2,6 M comprometidos no es un
descuadre, es un CDP con saldo. Llamarlo diferencia sería inventar un problema,
igual que pasaba con los contratos de 2025 antes de mirar el ejercicio.

LO QUE NO SE PUEDE PUBLICAR, Y SE DICE
---------------------------------------
- **El saldo de los 2.168 CDP que no están en innovaK.** No es que sea cero: es
  que nadie registró por cuánto se expidieron. La pantalla lo dice en la celda.
- **El proyecto de 1.605 CDP.** Llegan por el rubro de «Obligaciones por pagar
  Inversión vigencia anterior», que no identifica proyecto. Es el mismo límite
  que ya tiene la plata y no se arregla mirando más fuerte.
"""
from __future__ import annotations

#: Un CDP por número. Se agrega por `numero_de_cdp` y no por el par
#: `(n_interno_cdp, n_posicion_cdp)` porque el número es lo que la gente lee y
#: lo que innovaK registra. Medido: 2.173 números para 2.227 pares, o sea unos
#: pocos CDP con más de una posición — se suman, que es lo correcto.
_SQL_BOGDATA = """
SELECT c.numero_de_cdp                                      AS numero,
       max(c.n_interno_cdp)                                 AS n_interno,
       count(DISTINCT c.n_posicion_cdp)                     AS n_posiciones,
       sum(c.valor_neto)                                    AS comprometido,
       sum(c.autorizacion_giro)                             AS girado,
       count(*)                                             AS n_crp,
       count(DISTINCT c.no_compromiso)                      AS n_compromisos,
       max(c.ejercicio)                                     AS ejercicio,
       min(c.fecha_de_entrada)                              AS fecha,
       count(DISTINCT c.proyecto_id)                        AS n_proyectos,
       min(c.proyecto_id)                                   AS proyecto_id,
       max(c.texto_id_proyecto)                             AS proyecto_texto,
       max(c.rubro_desc)                                    AS rubro,
       bool_or(c.es_obligacion_por_pagar)                   AS por_pagar
FROM crp c
WHERE c.numero_de_cdp IS NOT NULL
GROUP BY 1
"""

#: Lo que innovaK registró. `numero` es texto en esta tabla y entero en el CRP,
#: así que se normaliza acá y no en el cruce: dejarlo para después es como se
#: cuelan los empates que no son.
_SQL_INNOVAK = """
SELECT k.id                                                 AS cdp_id,
       NULLIF(regexp_replace(COALESCE(k.numero, ''), '[^0-9]', '', 'g'), '')::bigint AS numero,
       k.valor                                              AS valor,
       k.fecha                                              AS fecha,
       COALESCE(NULLIF(k.descripcion, ''), k.objeto)        AS descripcion,
       p.id                                                 AS proyecto_id,
       p.codigo                                             AS proyecto_codigo,
       p.nombre                                             AS proyecto_nombre,
       (SELECT count(*) FROM contrato ct WHERE ct.cdp_id = k.id)      AS n_contratos,
       (SELECT sum(ct.valor) FROM contrato ct WHERE ct.cdp_id = k.id) AS valor_contratos
FROM cdp k
LEFT JOIN proyecto p ON p.id = k.proyecto_id
"""

CLASES = (
    "sin_numero",     # la cáscara: registrada en innovaK sin número que cruzar
    "solo_innovak",   # tiene número y BogData no lo mueve en este corte
    "solo_bogdata",   # el CDP existe y nadie lo registró en el Plan
    "con_respaldo",   # está en las dos: acá SÍ se puede decir cuánto queda
)

GLOSA = {
    "sin_numero": "Registrado en innovaK sin número de CDP: no hay con qué cruzarlo.",
    "solo_innovak": "Registrado en innovaK y sin movimiento en el corte de BogData.",
    "solo_bogdata": "Expedido según BogData y sin registrar en el Plan.",
    "con_respaldo": "Está en las dos fuentes: se puede decir cuánto queda libre.",
}

#: La cadena completa, en su orden, y de qué fuente sale cada escalón. Se
#: publica desde acá —no desde la pantalla— porque es doctrina del negocio y no
#: decoración: el rótulo se escribe donde se calcula la cifra.
#:
#: `campo` en `None` significa que ESTE archivo no lo trae. No es cero: es que
#: el eslabón no viene, y la pantalla tiene que decirlo distinto.
CADENA = (
    {"paso": "Apropiación", "que": "Plata autorizada en el presupuesto",
     "fuente": "Matriz PDL", "campo": None},
    {"paso": "CDP", "que": "Hay plata disponible para contratar esto",
     "fuente": "BogData", "campo": "cdps"},
    {"paso": "Proceso contractual", "que": "Se adelanta la contratación",
     "fuente": "SECOP II", "campo": None},
    {"paso": "Contrato", "que": "Se firma con un contratista",
     "fuente": "SECOP II / innovaK", "campo": None},
    {"paso": "CRP", "que": "La plata queda comprometida para ese contrato",
     "fuente": "BogData", "campo": "comprometido"},
    {"paso": "Ejecución", "que": "El contratista ejecuta",
     "fuente": "Matriz PDL", "campo": None},
    {"paso": "Obligación", "que": "Se reconoce lo que corresponde pagar",
     "fuente": "—", "campo": None},
    {"paso": "Giro", "que": "Sale efectivamente la plata",
     "fuente": "BogData (autorizado)", "campo": "girado"},
)

_CACHE: dict = {"datos": None, "hasta": 0.0}
_TTL_SEGUNDOS = 30


def _ahora() -> float:
    import time
    return time.monotonic()


def invalidar_cache() -> None:
    """Tira el caché. Para los tests, que escriben y releen en la misma
    transacción, donde 30 segundos son una eternidad."""
    _CACHE["datos"], _CACHE["hasta"] = None, 0.0


def _f(v):
    """A float, o `None`. Un vacío no se convierte en cero acá ni en ningún
    otro sitio del módulo."""
    return None if v is None else float(v)


def _totales_archivo(cur) -> dict:
    """Las cinco cifras de plata del corte, tal como vienen. `valor_neto` se
    rotula «comprometido» y NUNCA «gastado»: es la confusión que esta pantalla
    existe para no repetir."""
    cur.execute("""SELECT count(DISTINCT numero_de_cdp), sum(valor_crp),
                          sum(anulaciones), sum(valor_neto),
                          sum(autorizacion_giro), sum(com_sin_aut_giro)
                   FROM crp""")
    n_cdp, crp, anul, neto, giro, sin_aut = cur.fetchone()
    return {"cdps": n_cdp or 0, "expedido": _f(crp), "anulaciones": _f(anul),
            "comprometido": _f(neto), "girado": _f(giro),
            "sin_autorizar": _f(sin_aut)}


def _corte_crp(cur) -> dict:
    cur.execute("SELECT id, fecha_corte, vigencia, filas_leidas "
                "FROM crp_carga ORDER BY id DESC LIMIT 1")
    fila = cur.fetchone()
    if not fila:
        return {"carga_id": None, "fecha": None, "ejercicio": None, "filas": None}
    return {"carga_id": fila[0],
            "fecha": fila[1].isoformat() if fila[1] else None,
            "ejercicio": fila[2], "filas": fila[3]}


def _clasificar(bog, ik):
    """`(clase, saldo)`. El saldo es `None` mientras no estén las dos fuentes,
    y ese `None` significa «no se puede calcular», no «cero pesos»."""
    if ik is not None and ik.get("numero") is None:
        return "sin_numero", None
    if bog is None:
        return "solo_innovak", None
    if ik is None:
        return "solo_bogdata", None

    expedido, comprometido = ik.get("valor"), bog.get("comprometido")
    if expedido is None or comprometido is None:
        return "con_respaldo", None
    return "con_respaldo", expedido - comprometido


def _leer(cur) -> dict:
    if _CACHE["datos"] is not None and _ahora() < _CACHE["hasta"]:
        return _CACHE["datos"]

    corte = _corte_crp(cur)

    cur.execute(_SQL_BOGDATA)
    bogdata = {}
    for (num, n_int, n_pos, comp, giro, n_crp, n_comp, ejerc, fecha,
         n_proy, proy_id, proy_txt, rubro, por_pagar) in cur.fetchall():
        bogdata[num] = {
            "n_interno": n_int, "n_posiciones": n_pos,
            "comprometido": _f(comp), "girado": _f(giro),
            "n_crp": n_crp, "n_compromisos": n_comp, "ejercicio": ejerc,
            "fecha": fecha.isoformat() if fecha else None,
            # El proyecto solo se afirma cuando el CDP toca uno: con dos o más
            # nombrar el primero sería atribuir plata a quien no le toca.
            "proyecto_id": proy_id if n_proy == 1 else None,
            "proyecto_texto": proy_txt, "n_proyectos": n_proy or 0,
            "rubro": rubro, "por_pagar": bool(por_pagar),
        }

    cur.execute(_SQL_INNOVAK)
    innovak, sin_numero = {}, []
    for (cid, num, valor, fecha, desc, proy_id, pcod, pnom,
         n_ctr, val_ctr) in cur.fetchall():
        fila = {
            "cdp_id": cid, "numero": num, "valor": _f(valor),
            "fecha": fecha.isoformat() if fecha else None,
            "descripcion": desc, "proyecto_id": proy_id,
            "proyecto_codigo": pcod, "proyecto_nombre": pnom,
            "n_contratos": n_ctr or 0, "valor_contratos": _f(val_ctr),
        }
        if num is None:
            sin_numero.append(fila)
        else:
            innovak[num] = fila

    filas = []
    for num in sorted(set(bogdata) | set(innovak)):
        bog, ik = bogdata.get(num), innovak.get(num)
        clase, saldo = _clasificar(bog, ik)
        filas.append({
            "numero": num, "bogdata": bog, "innovak": ik,
            "clase": clase, "glosa": GLOSA[clase], "saldo": saldo,
        })

    # Las cáscaras van al final y con su clase propia: no tienen número, así
    # que no pueden ordenarse entre los demás ni cruzarse con nada. Esconderlas
    # sería peor — son justamente las que hay que completar.
    for ik in sin_numero:
        filas.append({
            "numero": None, "bogdata": None, "innovak": ik,
            "clase": "sin_numero", "glosa": GLOSA["sin_numero"], "saldo": None,
        })

    datos = {"filas": filas, "corte": corte,
             "archivo": _totales_archivo(cur)}
    _CACHE["datos"], _CACHE["hasta"] = datos, _ahora() + _TTL_SEGUNDOS
    return datos


def _suma(valores):
    vivos = [v for v in valores if v is not None]
    return sum(vivos) if vivos else None


def _filtrar(filas, clase=None, q="", proyecto=None):
    if clase:
        filas = [f for f in filas if f["clase"] == clase]
    if proyecto:
        filas = [f for f in filas
                 if (f["innovak"] or {}).get("proyecto_codigo") == proyecto]
    q = (q or "").strip().lower()
    if q:
        def coincide(f):
            campos = [str(f["numero"] or "")]
            b, i = f.get("bogdata") or {}, f.get("innovak") or {}
            campos += [b.get("proyecto_texto"), b.get("rubro"),
                       i.get("descripcion"), i.get("proyecto_nombre")]
            return any(q in (c or "").lower() for c in campos)
        filas = [f for f in filas if coincide(f)]
    return filas


def resumen(filas, corte, archivo=None) -> dict:
    """Cuántos CDP y cuánta plata en cada clase, cada cifra con su fuente."""
    por_clase = {}
    for c in CLASES:
        g = [f for f in filas if f["clase"] == c]
        por_clase[c] = {
            "n": len(g),
            "glosa": GLOSA[c],
            "expedido_innovak": _suma([(f["innovak"] or {}).get("valor") for f in g]),
            "comprometido_bogdata": _suma([(f["bogdata"] or {}).get("comprometido") for f in g]),
            "girado_bogdata": _suma([(f["bogdata"] or {}).get("girado") for f in g]),
            "saldo": _suma([f["saldo"] for f in g]),
        }
    return {
        "n": len(filas),
        "por_clase": por_clase,
        "cobertura": {
            "en_bogdata": sum(1 for f in filas if f["bogdata"]),
            "en_innovak": sum(1 for f in filas if f["innovak"]),
            "con_saldo": sum(1 for f in filas if f["saldo"] is not None),
            "con_proyecto": sum(1 for f in filas
                                if (f["bogdata"] or {}).get("proyecto_id")
                                or (f["innovak"] or {}).get("proyecto_codigo")),
        },
        "corte_crp": corte,
        # La cadena con su cifra donde la hay, y sin inventarla donde no.
        "cadena": [
            {**paso,
             "valor": (archivo or {}).get(paso["campo"]) if paso["campo"] else None,
             "medido": bool(paso["campo"])}
            for paso in CADENA
        ],
        "archivo": archivo or {},
    }


def cdps(clase=None, q="", proyecto=None, page=1, por=25, cursor=None) -> dict:
    """La lista de CDP con sus dos fuentes al lado, paginada.

    El resumen se calcula sobre el universo filtrado por `q` y `proyecto`, no
    sobre la página ni sobre la clase: un contador que cambia al elegir una
    clase no sirve para decidir por dónde empezar.
    """
    from django.db import connection
    import math

    def _con(cur):
        datos = _leer(cur)
        universo = _filtrar(datos["filas"], q=q, proyecto=proyecto)
        visibles = _filtrar(universo, clase=clase)
        por_pag = max(1, min(int(por or 25), 100))
        pagina = max(1, int(page or 1))
        desde = (pagina - 1) * por_pag
        return {
            "items": visibles[desde:desde + por_pag],
            "count": len(visibles),
            "page": pagina,
            "pages": max(1, math.ceil(len(visibles) / por_pag)),
            "resumen": resumen(universo, datos["corte"], datos.get("archivo")),
        }

    if cursor is not None:
        return _con(cursor)
    with connection.cursor() as cur:
        return _con(cur)


#: Los CRP que cuelgan de un CDP. Es el nivel que faltaba: el CDP dice cuánta
#: plata se reservó, el CRP dice a quién se le comprometió y por cuánto. Sin
#: esto la pantalla llegaba hasta «se comprometieron $X» y no decía con quién.
#:
#: `n_interno_crp` y `n_posicion_crp` son la llave natural de la fila (DDL 028);
#: se publican porque son lo que permite rastrear un CRP en BogData cuando dos
#: comparten número de compromiso.
_SQL_CRP_DE_CDP = """
SELECT c.numero_de_crp,
       c.n_interno_crp,
       c.n_posicion_crp,
       c.no_compromiso,
       c.compromiso_numero,
       c.compromiso_anio,
       c.tipo_compromiso_desc,
       c.nombre_bp_beneficiario,
       c.numero_doc_bp_beneficiario,
       c.objeto,
       c.valor_crp,
       c.anulaciones,
       c.valor_neto,
       c.autorizacion_giro,
       c.com_sin_aut_giro,
       c.rubro_codigo,
       c.rubro_desc,
       c.descripcion_concepto_gasto,
       c.texto_id_proyecto,
       c.fecha_registro,
       c.fecha_inicio_compromiso,
       c.fecha_fin_compromiso,
       c.es_obligacion_por_pagar,
       c.proyecto_id
FROM crp c
WHERE c.numero_de_cdp = %s
ORDER BY c.valor_neto DESC NULLS LAST, c.numero_de_crp
"""


def crps_del_cdp(numero, cursor=None) -> dict:
    """Los CRP de un CDP, con el enlace a lo que innovaK ya sabe del contrato.

    `en_el_plan` dice si ese compromiso está registrado como contrato interno.
    Es el salto que cierra la cadena **CDP → CRP → contrato → proyecto**: hasta
    acá se podía ver la plata reservada y comprometida, pero no a qué parte del
    Plan sirve.

    `girado` sale de `autorizacion_giro`, que es lo que BogData autorizó pagar.
    No se mezcla con el `valor_pagado` de SECOP, que mide el acumulado del
    contrato sin vigencia y escribe 0 también cuando no sabe.
    """
    from django.db import connection

    def _con(cur):
        cur.execute(_SQL_CRP_DE_CDP, [numero])
        filas = cur.fetchall()

        # Qué compromisos son contratos nuestros. En bloque y no uno por uno:
        # un CDP puede traer 36 CRP y serían 36 consultas por expandir una fila.
        llaves = {(f[4], f[5]) for f in filas if f[4] and f[5]}
        internos = {}
        if llaves:
            cur.execute(
                "SELECT contrato_numero, contrato_vigencia, id, valor "
                "FROM contrato WHERE contrato_numero = ANY(%s) "
                "  AND contrato_vigencia = ANY(%s)",
                [[k[0] for k in llaves], [k[1] for k in llaves]])
            internos = {(n, v): {"contrato_id": i, "valor": _f(val)}
                        for n, v, i, val in cur.fetchall()}

        items = []
        for f in filas:
            interno = internos.get((f[4], f[5]))
            items.append({
                "numero_crp": f[0], "n_interno": f[1], "n_posicion": f[2],
                "no_compromiso": f[3],
                "compromiso_numero": f[4], "compromiso_anio": f[5],
                "tipo": f[6],
                "beneficiario": f[7], "documento": f[8],
                "objeto": f[9],
                "valor_crp": _f(f[10]), "anulaciones": _f(f[11]),
                "comprometido": _f(f[12]), "girado": _f(f[13]),
                "sin_autorizar": _f(f[14]),
                "rubro_codigo": f[15], "rubro": f[16],
                "concepto_gasto": f[17], "proyecto_texto": f[18],
                "fecha_registro": f[19].isoformat() if f[19] else None,
                "fecha_inicio": f[20].isoformat() if f[20] else None,
                "fecha_fin": f[21].isoformat() if f[21] else None,
                "por_pagar": bool(f[22]), "proyecto_id": f[23],
                "en_el_plan": interno is not None,
                "innovak": interno,
            })

        return {
            "numero_cdp": numero,
            "items": items,
            "totales": {
                "n": len(items),
                "valor_crp": _suma([i["valor_crp"] for i in items]),
                "anulaciones": _suma([i["anulaciones"] for i in items]),
                "comprometido": _suma([i["comprometido"] for i in items]),
                "girado": _suma([i["girado"] for i in items]),
                "sin_autorizar": _suma([i["sin_autorizar"] for i in items]),
                "en_el_plan": sum(1 for i in items if i["en_el_plan"]),
            },
        }

    if cursor is not None:
        return _con(cursor)
    with connection.cursor() as cur:
        return _con(cur)
