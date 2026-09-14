"""En qué se gasta la plata del Fondo. Una sola implementación.

QUÉ REEMPLAZA
-------------
`/plan/conceptos` servía la tabla interna `concepto_gasto`, que tiene **una
fila y es una prueba**: código 230201, nombre «prueba concepto», descripción
«pruebas de concepto». Nada la referencia —`contrato_actividad_plan` tiene 15
filas y las 15 traen `concepto_gasto_id` en NULL—, así que la pantalla era un
CRUD sobre un dato de ensayo que nadie usa.

El gasto real está en el CRP de BogData y se puede agrupar de tres formas, que
son tres preguntas distintas y por eso la pantalla las ofrece como tres ejes:

    tipo de compromiso ..... EN QUÉ se gasta      20 valores
    modalidad de selección . CÓMO se contrató     13 valores
    rubro .................. DE DÓNDE sale        49 valores

EL «CONCEPTO DE GASTO» DEL ARCHIVO NO SIRVE PARA ESTO, y conviene dejarlo
escrito para que no se vuelva a intentar: `concepto_gasto_codigo` solo tiene
CUATRO valores en las 2.630 filas —«NO APLICA», dos de obligaciones por pagar y
uno de funcionamiento—, que es el mismo corte que ya hace el rubro y con menos
detalle. El nombre promete un desglose del gasto y entrega un bucket contable.

LO QUE SE PUBLICA POR GRUPO, Y CON QUÉ NOMBRE
----------------------------------------------
Los compromisos se cuentan **distintos** (`no_compromiso`), no filas: un
contrato con siete CRP es un compromiso, no siete. Contar filas inflaría los
grupos donde más se adiciona.

Y las tres cifras de plata van con el rótulo de la cadena, nunca como «gasto»:

    comprometido    lo que quedó afectado a un contrato
    girado          lo AUTORIZADO a girar, que no es el pago hecho
    sin autorizar   comprometido que todavía no tiene autorización

`comprometido = girado + sin autorizar`, y esa identidad la protege un test: si
deja de cumplirse es que se cambió de columna sin cambiar el rótulo.
"""
from __future__ import annotations

#: Los tres ejes. La llave es lo que viaja en la URL; `columna` es de dónde
#: sale y vive acá y no en la vista para que no se puedan pedir columnas
#: arbitrarias desde fuera.
EJES = {
    "tipo": {
        "columna": "tipo_compromiso_desc",
        "titulo": "Tipo de compromiso",
        "pregunta": "En qué se gasta",
    },
    "modalidad": {
        "columna": "modalidad_desc",
        "titulo": "Modalidad de selección",
        "pregunta": "Cómo se contrató",
    },
    "rubro": {
        "columna": "rubro_desc",
        "titulo": "Rubro",
        "pregunta": "De dónde sale la plata",
    },
}

_SQL = """
SELECT COALESCE(NULLIF(trim(c.{col}), ''), '(sin declarar)')  AS grupo,
       count(DISTINCT c.no_compromiso)                        AS compromisos,
       count(*)                                               AS n_crp,
       count(DISTINCT c.numero_de_cdp)                        AS cdps,
       count(DISTINCT c.tercero_id)                           AS terceros,
       sum(c.valor_neto)                                      AS comprometido,
       sum(c.autorizacion_giro)                               AS girado,
       sum(c.com_sin_aut_giro)                                AS sin_autorizar,
       count(DISTINCT c.tercero_id) FILTER (WHERE t.es_juridica IS TRUE)  AS juridicas,
       count(DISTINCT c.tercero_id) FILTER (WHERE t.es_juridica IS FALSE) AS naturales
FROM crp c
LEFT JOIN tercero_sap t ON t.id = c.tercero_id
{where}
GROUP BY 1
ORDER BY sum(c.valor_neto) DESC NULLS LAST
"""

_CACHE: dict = {"datos": {}, "hasta": 0.0}
_TTL_SEGUNDOS = 30


def _ahora() -> float:
    import time
    return time.monotonic()


def invalidar_cache() -> None:
    _CACHE["datos"], _CACHE["hasta"] = {}, 0.0


def _f(v):
    return None if v is None else float(v)


def _suma(valores):
    vivos = [v for v in valores if v is not None]
    return sum(vivos) if vivos else None


def _corte(cur) -> dict:
    cur.execute("SELECT id, fecha_corte, vigencia, filas_leidas "
                "FROM crp_carga ORDER BY id DESC LIMIT 1")
    fila = cur.fetchone()
    if not fila:
        return {"carga_id": None, "fecha": None, "ejercicio": None, "filas": None}
    return {"carga_id": fila[0],
            "fecha": fila[1].isoformat() if fila[1] else None,
            "ejercicio": fila[2], "filas": fila[3]}


def gasto(eje="tipo", vigencia=None, cursor=None) -> dict:
    """El gasto agrupado por uno de los tres ejes, de mayor a menor.

    `vigencia` filtra por AÑO DEL COMPROMISO, que es el corte del PDL y no
    `es_obligacion_por_pagar`: de las obligaciones por pagar, $93.209 M son de
    compromisos de 2025 y son ejecución legítima del Plan. Cortar por la
    bandera se los llevaría junto con los de administraciones anteriores.
    """
    from django.db import connection

    if eje not in EJES:
        eje = "tipo"
    clave = (eje, vigencia)

    if _CACHE["datos"].get(clave) is not None and _ahora() < _CACHE["hasta"]:
        return _CACHE["datos"][clave]

    where, params = "", []
    if vigencia is not None:
        where = "WHERE c.compromiso_anio = %s"
        params = [vigencia]

    def _con(cur):
        cur.execute(_SQL.format(col=EJES[eje]["columna"], where=where), params)
        items = [{
            "grupo": g, "compromisos": comp, "n_crp": n_crp, "cdps": cdps,
            "terceros": terc,
            "comprometido": _f(cm), "girado": _f(gi), "sin_autorizar": _f(sa),
            "juridicas": jur, "naturales": nat,
        } for (g, comp, n_crp, cdps, terc, cm, gi, sa, jur, nat) in cur.fetchall()]

        total_c = _suma([i["comprometido"] for i in items])
        # El peso de cada grupo sobre el total, calculado acá y no en la
        # pantalla: si lo hiciera cada vista, dos pantallas darían dos
        # porcentajes del mismo grupo.
        for i in items:
            i["pct"] = (round(100.0 * i["comprometido"] / total_c, 1)
                        if total_c and i["comprometido"] is not None else None)

        return {
            "eje": eje,
            "ejes": [{"clave": k, **v} for k, v in EJES.items()],
            "vigencia": vigencia,
            "items": items,
            "totales": {
                "grupos": len(items),
                # COUNT(DISTINCT) sobre el universo, y NO la suma de los
                # grupos. Un compromiso con varios CRP puede caer en más de un
                # grupo —dos rubros, dos modalidades— y entonces se contaba una
                # vez por grupo: el encabezado decía 2.307 en «tipo», 2.270 en
                # «modalidad» y 2.352 en «rubro» cuando los compromisos
                # distintos son 2.265. O sea que el total CAMBIABA al cambiar
                # de pestaña sin que se filtrara nada, que es lo que lo delató.
                #
                # La plata nunca estuvo mal —$226.744.982.139 en los tres
                # ejes—: se duplicaba el CONTEO, no el valor.
                "compromisos": _compromisos_distintos(cur, where, params),
                "comprometido": total_c,
                "girado": _suma([i["girado"] for i in items]),
                "sin_autorizar": _suma([i["sin_autorizar"] for i in items]),
            },
            "corte_crp": _corte(cur),
            "vigencias": _vigencias(cur),
        }

    if cursor is not None:
        datos = _con(cursor)
    else:
        with connection.cursor() as cur:
            datos = _con(cur)

    _CACHE["datos"][clave] = datos
    _CACHE["hasta"] = _ahora() + _TTL_SEGUNDOS
    return datos


def _compromisos_distintos(cur, where, params) -> int:
    """Cuántos compromisos distintos hay en el universo, sea cual sea el eje.

    Mismo `where` que la consulta de los grupos, para que el total y las filas
    hablen del mismo conjunto. Es independiente del eje a propósito: agrupar no
    cambia cuántos compromisos hay.
    """
    cur.execute(
        f"SELECT COUNT(DISTINCT c.no_compromiso) FROM crp c {where}", params)
    fila = cur.fetchone()
    return int(fila[0] or 0) if fila else 0


def _vigencias(cur):
    """Los años que hay, del dato y no de una lista escrita a mano."""
    cur.execute("SELECT DISTINCT compromiso_anio FROM crp "
                "WHERE compromiso_anio IS NOT NULL ORDER BY 1 DESC")
    return [r[0] for r in cur.fetchall()]
