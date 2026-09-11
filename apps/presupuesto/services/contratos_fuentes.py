"""Un contrato visto por sus TRES fuentes a la vez. Una sola implementación.

PARA QUÉ EXISTE
---------------
La pantalla de contratos oficiales mostraba SECOP y marcaba si el contrato
estaba o no en innovaK. Faltaba la tercera fuente —BogData— que es justo la
que tiene la plata, y faltaba lo que pidió Alex: **poder ver dónde está el
error según el dato**, no que el sistema elija un número y esconda los otros.

Acá cada contrato se publica con lo que dice cada fuente, con su rótulo, y al
lado una CLASE de concordancia que dice si las cifras son comparables entre sí
y, cuando no lo son, por qué.

QUIÉN MANDA PARA CADA DATO (del mapa de fuentes, 2026-09-10)
------------------------------------------------------------
    el hecho contractual ...... SECOP II   número, objeto, contratista, estado
    la plata del presupuesto .. BogData    comprometido y girado del ejercicio
    el enlace con el Plan ..... innovaK    proyecto, actividad, meta, área

Ninguna manda sobre las otras dos: miden cosas distintas. Por eso acá no hay
una columna «valor» sino tres, cada una con su nombre.

LA LLAVE, Y POR QUÉ NO BASTA
-----------------------------
Las tres fuentes se cruzan por `(número, año)`: SECOP lo trae dentro de
`referencia_contrato` (`CPS-815-2025`), BogData en `compromiso_numero` y
`compromiso_anio`, innovaK en `contrato_numero` y `contrato_vigencia`.

Esa llave **empata de más**. Medido: de 1.682 contratos de 2025 en adelante
que empatan entre SECOP y BogData, **99 tienen un contratista distinto en cada
fuente** — el caso más claro es el `628-2026`, donde BogData agrupa bajo un
mismo número a una persona natural, a IDARTES y a la Secretaría de Cultura.
Cuando el documento del contratista no coincide, acá **no se comparan valores**:
la clase es `identidad_dudosa` y se muestran los dos nombres para que alguien
lo mire. Comparar cifras de dos contratos distintos produce una diferencia
inventada, que es peor que no tener el dato.

LA REGLA QUE EVITA LA DIFERENCIA FANTASMA
------------------------------------------
**El archivo del CRP es un corte de UN ejercicio.** El del 7 de septiembre de
2026 trae 2.630 filas y las 2.630 son del ejercicio 2026, sin excepción. Para
un contrato de 2026 su `valor_neto` es el compromiso del año y se puede poner
al lado del valor del contrato en SECOP. Para uno de 2025 es **solo el saldo
que quedó como obligación por pagar**, no el compromiso original.

Lo que pasa si se ignora, medido:

    contratos de 2026 ... 731, de los cuales 703 coinciden al peso (96,2 %)
    contratos de 2025 ... 848, de los cuales 227 coinciden

y esos 621 restantes de 2025 suman $42.195.500.077 de «diferencia» que no
existe: es el pedazo del contrato que ya se pagó en su propia vigencia y por
eso no viaja al corte siguiente. Acá esos casos son `fuera_de_corte`: se
publican las dos cifras con su rótulo y **no se restan**.

LO QUE UNA FUENTE NO VE NO ES UN CERO
--------------------------------------
Vale para las dos direcciones y las dos están medidas:

- 308 contratos de SECOP de 2025 en adelante no tienen CRP en este corte
  ($14.546 M). Los de 2025 casi todos porque ya se pagaron.
- 13 compromisos de BogData no tienen contrato en SECOP ($37.183 M), y no es
  un descuido: son **órdenes de compra** (Tienda Virtual) y **convenios
  interadministrativos**, que no se publican en el módulo de contratos de
  SECOP II. El mayor es el `847-2026` con Integración Social, $25.884 M,
  girado por completo.
- `secop_contrato.valor_pagado` **nunca llega en NULL**: 3.123 de 3.123 filas
  lo traen, así que «no giró» y «nadie lo cargó» son el mismo cero. 152
  contratos de 2025 en adelante, por $70.204 M, están en cero. Por eso el
  pagado de SECOP se publica como dato de esa fuente y jamás como el girado
  del contrato.
"""
from __future__ import annotations

#: Cómo se lee el número y el año dentro de la referencia de SECOP
#: (`CPS-815-2025` → 815, 2025). Es el mismo patrón que ya usa la lista de
#: contratos oficiales en `apps.dashboard.services.kpis_presupuesto`; vive
#: repetido a propósito mientras esa pantalla siga en la app de dashboard.
_RX_REF = r'^[A-Z]+\s*-\s*0*(\d+)\s*-\s*(\d{4})'

#: Solo dígitos, para poder comparar documentos que vienen con puntos o guiones.
_SOLO_DIGITOS = r"regexp_replace(coalesce({col}, ''), '[^0-9]', '', 'g')"

_SQL_SECOP = f"""
SELECT ((regexp_match(upper(trim(s.referencia_contrato)), '{_RX_REF}'))[1])::int  AS numero,
       ((regexp_match(upper(trim(s.referencia_contrato)), '{_RX_REF}'))[2])::int  AS anio,
       max(s.referencia_contrato)                          AS referencia,
       max(s.tipo_contrato)                                AS tipo,
       max(s.estado_contrato)                              AS estado,
       max(s.objeto_contrato)                              AS objeto,
       max(s.proveedor)                                    AS contratista,
       max({_SOLO_DIGITOS.format(col='s.documento_proveedor')}) AS documento,
       sum(s.valor_contrato)                               AS valor,
       sum(s.valor_pagado)                                 AS pagado,
       max(s.url_proceso)                                  AS url,
       count(*)                                            AS n_filas
FROM secop_contrato s
WHERE s.referencia_contrato ~ '{_RX_REF}'
GROUP BY 1, 2
"""

_SQL_BOGDATA = f"""
SELECT c.compromiso_numero                                 AS numero,
       c.compromiso_anio                                   AS anio,
       max(c.no_compromiso)                                AS no_compromiso,
       max(c.tipo_compromiso_desc)                         AS tipo,
       max(c.nombre_bp_beneficiario)                       AS contratista,
       array_agg(DISTINCT {_SOLO_DIGITOS.format(col='c.numero_doc_bp_beneficiario')}) AS documentos,
       sum(c.valor_neto)                                   AS comprometido,
       sum(c.autorizacion_giro)                            AS girado,
       max(c.rubro_desc)                                   AS rubro,
       max(c.ejercicio)                                    AS ejercicio,
       bool_or(c.es_obligacion_por_pagar)                  AS por_pagar,
       count(*)                                            AS n_crp
FROM crp c
WHERE c.compromiso_numero IS NOT NULL AND c.compromiso_anio IS NOT NULL
GROUP BY 1, 2
"""

#: innovaK no tiene una sola vía para saber de qué proyecto es un contrato:
#: `contrato_proyecto` y `contrato_actividad_plan` son dos caminos y hay
#: contratos que solo llegan por el segundo. La unión es la misma que usa el
#: panel de área; leerlo por una sola vía dejaba áreas enteras en $0.
_SQL_INNOVAK = """
SELECT k.contrato_numero                                   AS numero,
       k.contrato_vigencia                                 AS anio,
       min(k.id)                                           AS contrato_id,
       max(k.valor)                                        AS valor,
       count(DISTINCT p.id)                                AS n_proyectos,
       min(p.id)                                           AS proyecto_id,
       min(p.codigo)                                       AS proyecto_codigo,
       min(p.nombre)                                       AS proyecto_nombre
FROM contrato k
LEFT JOIN (
    SELECT contrato_id, proyecto_id FROM contrato_proyecto
    UNION
    SELECT cap.contrato_id, ap.proyecto_id
    FROM contrato_actividad_plan cap
    JOIN actividad_plan ap ON ap.id = cap.actividad_plan_id
) v ON v.contrato_id = k.id
LEFT JOIN proyecto p ON p.id = v.proyecto_id
WHERE k.contrato_numero IS NOT NULL AND k.contrato_vigencia IS NOT NULL
GROUP BY 1, 2
"""

#: Las clases de concordancia, en el orden en que se deciden. El orden importa:
#: la identidad se resuelve ANTES que el valor, porque comparar pesos de dos
#: contratos distintos produce una diferencia que no significa nada.
CLASES = (
    "solo_secop",        # hecho contractual sin respaldo presupuestal en el corte
    "solo_bogdata",      # compromiso sin espejo en SECOP (órdenes de compra, convenios)
    "identidad_dudosa",  # la llave empata pero el contratista no: no se compara
    "fuera_de_corte",    # el año del compromiso no es el ejercicio del CRP
    "valor_distinto",    # mismo contratista, mismo ejercicio, cifras distintas
    "acuerdo",           # las fuentes que hay dicen lo mismo
)

#: Qué significa cada clase, en la lengua de quien lee el tablero. Se publica
#: con los datos —el rótulo se escribe donde se calcula la cifra— para que la
#: pantalla no tenga que inventar su propia glosa y las dos se separen.
GLOSA = {
    "solo_secop": "Está en SECOP y no tiene registro presupuestal en este corte.",
    "solo_bogdata": "Tiene registro presupuestal y no está en el espejo de SECOP.",
    "identidad_dudosa": "El número coincide pero el contratista no: puede ser otro contrato.",
    "fuera_de_corte": "El compromiso es de una vigencia anterior al corte; las cifras no son comparables.",
    "valor_distinto": "Misma vigencia y mismo contratista, con cifras distintas.",
    "acuerdo": "Las fuentes disponibles coinciden.",
}

_CACHE: dict = {"datos": None, "hasta": 0.0}
_TTL_SEGUNDOS = 30


def _ahora() -> float:
    import time
    return time.monotonic()


def invalidar_cache() -> None:
    """Tira el caché. Para los tests, que escriben y releen en la misma
    transacción, donde 30 segundos son una eternidad."""
    _CACHE["datos"], _CACHE["hasta"] = None, 0.0


def _corte_crp(cur) -> dict:
    """Qué corte del CRP se está leyendo. Sin esto no se puede decir si una
    cifra es comparable: es la fecha y el ejercicio los que lo deciden."""
    cur.execute("SELECT id, fecha_corte, vigencia, filas_leidas "
                "FROM crp_carga ORDER BY id DESC LIMIT 1")
    fila = cur.fetchone()
    if not fila:
        return {"carga_id": None, "fecha": None, "ejercicio": None, "filas": None}
    return {"carga_id": fila[0],
            "fecha": fila[1].isoformat() if fila[1] else None,
            "ejercicio": fila[2], "filas": fila[3]}


def _clasificar(secop, bog, ejercicio):
    """La clase de concordancia y, cuando procede, la diferencia.

    Devuelve `(clase, diferencia)` donde `diferencia` es `None` siempre que la
    comparación no sea legítima. Un `None` acá no es «no hay diferencia»: es
    «no se puede restar», y la pantalla tiene que decirlo distinto.
    """
    if bog is None:
        return "solo_secop", None
    if secop is None:
        return "solo_bogdata", None

    doc = secop.get("documento") or ""
    docs = [d for d in (bog.get("documentos") or []) if d]
    if doc and docs and doc not in docs:
        return "identidad_dudosa", None

    # El corte del CRP manda: fuera de su ejercicio, `valor_neto` es el saldo
    # que sobrevivió al cierre, no el compromiso. Restarlo del valor del
    # contrato inventa una diferencia del tamaño de lo ya pagado.
    if ejercicio is not None and bog.get("anio") != ejercicio:
        return "fuera_de_corte", None

    v_secop, v_bog = secop.get("valor"), bog.get("comprometido")
    if v_secop is None or v_bog is None:
        return "acuerdo", None
    if abs(v_secop - v_bog) <= 1:
        return "acuerdo", 0.0
    return "valor_distinto", v_secop - v_bog


def _leer(cur) -> dict:
    """Las tres fuentes cruzadas por `(número, año)`, cacheadas 30 s.

    Tres consultas y un cruce en Python, no un `FULL OUTER JOIN` de tres vías:
    el universo son unos miles de filas y el join en SQL obligaba a repetir el
    `regexp_match` en cada rama, que es donde se cuelan las diferencias entre
    una consulta y la siguiente.
    """
    if _CACHE["datos"] is not None and _ahora() < _CACHE["hasta"]:
        return _CACHE["datos"]

    corte = _corte_crp(cur)
    ejercicio = corte.get("ejercicio")

    cur.execute(_SQL_SECOP)
    secop = {}
    for (num, anio, ref, tipo, estado, objeto, contratista, doc,
         valor, pagado, url, n_filas) in cur.fetchall():
        secop[(num, anio)] = {
            "referencia": ref, "tipo": tipo, "estado": estado, "objeto": objeto,
            "contratista": contratista, "documento": doc,
            "valor": float(valor) if valor is not None else None,
            # `pagado` se publica como dato de SECOP y nunca como el girado del
            # contrato: la fuente escribe 0 también cuando no sabe.
            "pagado": float(pagado) if pagado is not None else None,
            "url": url, "n_filas": n_filas,
        }

    cur.execute(_SQL_BOGDATA)
    bogdata = {}
    for (num, anio, noc, tipo, contratista, docs, comprometido, girado,
         rubro, ejerc, por_pagar, n_crp) in cur.fetchall():
        bogdata[(num, anio)] = {
            "no_compromiso": noc, "tipo": tipo, "contratista": contratista,
            "documentos": list(docs or []), "anio": anio,
            "comprometido": float(comprometido) if comprometido is not None else None,
            "girado": float(girado) if girado is not None else None,
            "rubro": rubro, "ejercicio": ejerc,
            "por_pagar": bool(por_pagar), "n_crp": n_crp,
        }

    cur.execute(_SQL_INNOVAK)
    innovak = {}
    for (num, anio, cid, valor, n_proy, pid, pcod, pnom) in cur.fetchall():
        innovak[(num, anio)] = {
            "contrato_id": cid,
            "valor": float(valor) if valor is not None else None,
            "n_proyectos": n_proy or 0,
            "proyecto_id": pid, "proyecto_codigo": pcod, "proyecto_nombre": pnom,
        }

    filas = []
    for llave in sorted(set(secop) | set(bogdata) | set(innovak)):
        num, anio = llave
        s, b, k = secop.get(llave), bogdata.get(llave), innovak.get(llave)
        clase, diferencia = _clasificar(s, b, ejercicio)
        filas.append({
            "numero": num, "anio": anio,
            "referencia": (s or {}).get("referencia") or (b or {}).get("no_compromiso")
                          or f"{num}-{anio}",
            "secop": s, "bogdata": b, "innovak": k,
            "en_el_plan": k is not None and bool(k.get("proyecto_codigo")),
            "clase": clase, "glosa": GLOSA[clase], "diferencia": diferencia,
        })

    datos = {"filas": filas, "corte": corte}
    _CACHE["datos"], _CACHE["hasta"] = datos, _ahora() + _TTL_SEGUNDOS
    return datos


def _suma(valores):
    """La suma de lo que hay, o `None` si no hay nada que sumar. Igual que en
    `plata_matriz`: un `COALESCE(..., 0)` convierte «no se sabe» en «cero»."""
    vivos = [v for v in valores if v is not None]
    return sum(vivos) if vivos else None


def _filtrar(filas, vigencia=None, clase=None, q="", solo_plan=None):
    if vigencia is not None:
        filas = [f for f in filas if f["anio"] == vigencia]
    if clase:
        filas = [f for f in filas if f["clase"] == clase]
    if solo_plan is True:
        filas = [f for f in filas if f["en_el_plan"]]
    elif solo_plan is False:
        filas = [f for f in filas if not f["en_el_plan"]]
    q = (q or "").strip().lower()
    if q:
        def coincide(f):
            campos = [f["referencia"]]
            for fuente in ("secop", "bogdata"):
                d = f.get(fuente) or {}
                campos += [d.get("contratista"), d.get("objeto")]
            return any(q in (c or "").lower() for c in campos)
        filas = [f for f in filas if coincide(f)]
    return filas


def resumen(filas, corte) -> dict:
    """Cuántos contratos y cuánta plata hay en cada clase.

    Cada clase trae el total de **su propia fuente**, no un total mezclado: los
    de `solo_bogdata` no tienen valor en SECOP y sumarlos como cero diría que
    esos $37.183 M no existen.
    """
    por_clase = {}
    for c in CLASES:
        del_grupo = [f for f in filas if f["clase"] == c]
        por_clase[c] = {
            "n": len(del_grupo),
            "glosa": GLOSA[c],
            "valor_secop": _suma([(f["secop"] or {}).get("valor") for f in del_grupo]),
            "comprometido_bogdata": _suma(
                [(f["bogdata"] or {}).get("comprometido") for f in del_grupo]),
            "girado_bogdata": _suma(
                [(f["bogdata"] or {}).get("girado") for f in del_grupo]),
        }

    comparables = [f for f in filas if f["diferencia"] is not None]
    en_plan = [f for f in filas if f["en_el_plan"]]
    return {
        "n": len(filas),
        "por_clase": por_clase,
        # La cobertura de cada fuente sobre el mismo universo. Ninguna cifra
        # viaja sin ella: es lo que impide leer «$0 girado» como «no pagó».
        "cobertura": {
            "en_secop": sum(1 for f in filas if f["secop"]),
            "en_bogdata": sum(1 for f in filas if f["bogdata"]),
            "en_innovak": sum(1 for f in filas if f["innovak"]),
            "en_el_plan": len(en_plan),
            "comparables": len(comparables),
            "coinciden": sum(1 for f in comparables if f["diferencia"] == 0),
        },
        "corte_crp": corte,
    }


def contratos(vigencia=None, clase=None, q="", solo_plan=None,
              page=1, por=25, cursor=None) -> dict:
    """La lista de contratos con sus tres fuentes al lado, paginada.

    `resumen` se calcula SIEMPRE sobre el universo filtrado por `vigencia` y
    `q`, nunca sobre la página ni sobre la clase elegida: un contador que
    cambia al pasar de página no sirve para decidir por dónde empezar.
    """
    from django.db import connection
    import math

    def _con(cur):
        datos = _leer(cur)
        universo = _filtrar(datos["filas"], vigencia=vigencia, q=q)
        visibles = _filtrar(universo, clase=clase, solo_plan=solo_plan)
        por_pag = max(1, min(int(por or 25), 100))
        pagina = max(1, int(page or 1))
        desde = (pagina - 1) * por_pag
        return {
            "items": visibles[desde:desde + por_pag],
            "count": len(visibles),
            "page": pagina,
            "pages": max(1, math.ceil(len(visibles) / por_pag)),
            "resumen": resumen(universo, datos["corte"]),
            "vigencias": sorted({f["anio"] for f in datos["filas"]}, reverse=True),
        }

    if cursor is not None:
        return _con(cursor)
    with connection.cursor() as cur:
        return _con(cur)
