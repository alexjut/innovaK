"""La PLATA del Plan, leída de la Matriz PDL. Una sola implementación.

QUÉ ES «PLATA» ACÁ: pesos apropiados, comprometidos y girados por meta y por
vigencia, tal como los reporta la Alcaldía en su Matriz. NO es el avance
físico —unidades, motos, sedes, personas—, que se mide aparte y con otras
reglas en `avance_matriz`. Mezclar las dos cosas es de donde salieron media
docena de contradicciones en pantalla.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
El sistema no tenía UNA forma de responder «cuánta plata tiene esto».
Convivían seis registros y cada recuadro eligió el suyo sin declararlo
(medido el 2026-09-10):

    Matriz PDL ................. comprometido $224.853.665.855
    CRP de BogData (del PDL) ... comprometido $184.839.187.185
    Contratos de innovaK ....... $41.264.386.430 en 25 contratos
    SECOP, pagado .............. $4.769.318.038
    Espejo de Planeación ....... programado $667.578.460.000, parado hace 49 días
    `programa_cdp` ............. cero filas, o sea un «Asignado» que jamás deja de ser $0

El resultado no era un matiz: el tablero publicaba 11,0 % comprometido y
1,27 % girado sobre una Matriz que dice 59,7 % y 26,9 %, y doce de las
dieciséis áreas con plata comprometida abrían su panel y leían «$0» teniendo
$147.541.561.007. Es la misma forma que tenía el avance físico antes de
`avance_matriz`, y se cierra igual.

Decisión de Alex (2026-09-10): **una sola fuente para los indicadores —la
Matriz— y las demás al lado, como contraste, nunca dentro del cálculo.** Por
eso el contraste lo produce ESTE módulo y no cada pantalla: un contraste que
cada quien arma por su cuenta vuelve a ser un sexto libro en seis meses.

LAS CUATRO REGLAS
-----------------
1. **La plata SE SUMA; el avance físico no.** Al agrupar metas, los pesos se
   suman —son la misma unidad— mientras que los cumplimientos se promedian
   porque motos y personas no hacen un denominador. Son módulos hermanos con
   agregaciones deliberadamente distintas.

2. **`None` nunca es `0`.** 2027 y 2028 vienen enteramente vacías (0 de 78
   filas con valor, verificado), así que elegir 2027 en el selector tiene que
   decir «sin dato» y no «$0». Un `COALESCE(...,0)` acá convierte «todavía no
   se apropia» en «no se apropió», que es la acusación que este módulo viene
   a quitar.

3. **La vigencia se SUMA entre años, a diferencia del cumplimiento.** El
   cumplimiento es un porcentaje del año y sumarlo no significa nada; la
   apropiación de 2025 más la de 2026 sí es la apropiación de los dos años.
   Por eso acá el parámetro `vigencia` filtra, y sin él se acumula.

4. **Cada cifra viaja con su cobertura.** Cuántas metas y cuántos proyectos la
   sostienen. Una cifra sin cobertura invita a compararla con otra que mide
   otro universo, que es el defecto que produjo el «99,2 % contra 28,4 %» del
   proyecto 2780.

UNA FILA POR META Y VIGENCIA. Verificado: 312 filas, 78 códigos de meta, 30
proyectos, cero duplicados. Por eso acá no hay riesgo de fan-out —a diferencia
de `avance_matriz`, que cruza contra `meta_proyecto` y sí lo tiene—: la tabla
ya trae la plata atribuida a su proyecto.

OCHO FILAS SIN PROGRAMA. Son las metas 23771 y 23772 (posmedia del proyecto
2377) por sus cuatro vigencias: existen en la Matriz y no tienen fila propia en
el catálogo interno, porque las cubre una meta agrupada. Se agregan igual por
proyecto y por área —su plata NO se pierde— y quedan fuera solo del corte por
programa, que se declara en la cobertura en vez de disimularse.
"""
from __future__ import annotations

FUENTE = "matriz_pdl_alk"

#: Todo lo que se sabe de la plata de una meta, en UNA consulta. Las
#: agregaciones salen de acá en Python en vez de cuatro SQL parecidos: cuatro
#: consultas que se creen equivalentes se desincronizan en cuanto una cambie, y
#: entonces dos pantallas del mismo tablero dicen números distintos de la misma
#: plata — que es justo el defecto que este módulo viene a cerrar.
_SQL_BASE = """
    SELECT v.codigo_meta,
           v.proyecto_codigo,
           v.vigencia,
           v.apropiacion_poai,
           v.comprometido,
           v.girado,
           v.proyectado_pdl,
           p.id            AS proyecto_id,
           p.subgrupo_id,
           m.programa_id,
           s.nombre_oficial AS sector
    FROM presu_presupuesto_meta_vigencia v
    -- 312 de 312 cruzan, y ninguna clave normalizada está repetida.
    LEFT JOIN proyecto p      ON regexp_replace(p.codigo, '^0+', '')
                                 = v.proyecto_codigo::text
    -- 304 de 312: faltan las 8 de las dos metas sin fila propia (ver el
    -- encabezado). Su plata sí entra por proyecto y por área.
    LEFT JOIN metas m         ON m.codigo_meta = v.codigo_meta
    LEFT JOIN presu_sector s  ON s.id = m.sector_id
    WHERE v.fuente = %s
"""

_I_META, _I_PROY_COD, _I_VIGENCIA = 0, 1, 2
_I_APROP, _I_COMP, _I_GIRADO, _I_PROYECTADO = 3, 4, 5, 6
_I_PROY_ID, _I_SUBGRUPO, _I_PROGRAMA, _I_SECTOR = 7, 8, 9, 10

#: Las tres columnas de la cadena real de ejecución, en orden.
#: Apropiación → Comprometido → Girado. NO Proyectado → Comprometido → Girado:
#: el proyectado es la meta aspiracional del cuatrienio, no plata asignada.
CAMPOS = ("apropiacion", "comprometido", "girado")

_CACHE: dict = {"filas": None, "hasta": 0.0}
_TTL_SEGUNDOS = 30


def _ahora() -> float:
    import time
    return time.monotonic()


def invalidar_cache() -> None:
    """Tira el caché. Para los tests que escriben y releen en la misma
    transacción, donde 30 segundos son una eternidad."""
    _CACHE["filas"], _CACHE["hasta"] = None, 0.0


def _filas(cursor=None):
    """Las 312 filas de la Matriz, cacheadas 30 s.

    Mismo criterio que `avance_matriz`: la Matriz cambia cuando alguien sube un
    corte —unas pocas veces al mes—, así que un caché de segundos no puede
    servir un dato viejo de forma perceptible, y ata este módulo a nada.
    """
    from django.db import connection

    if _CACHE["filas"] is not None and _ahora() < _CACHE["hasta"]:
        return _CACHE["filas"]

    def _leer(cur):
        cur.execute(_SQL_BASE, [FUENTE])
        return cur.fetchall()

    if cursor is not None:
        filas = _leer(cursor)
    else:
        with connection.cursor() as cur:
            filas = _leer(cur)

    _CACHE["filas"], _CACHE["hasta"] = filas, _ahora() + _TTL_SEGUNDOS
    return filas


def _suma(valores):
    """La suma de lo que hay, o `None` si no hay nada que sumar.

    LA REGLA MÁS IMPORTANTE DE ESTE MÓDULO. `sum()` de una lista vacía da 0, y
    ese 0 se pinta idéntico a un cero medido: 2027 y 2028 no tienen ni una
    fila con valor, así que devolver 0 diría «no se apropió» donde lo cierto es
    «todavía no se apropia».
    """
    vivos = [float(v) for v in valores if v is not None]
    return sum(vivos) if vivos else None


def _acumular(filas) -> dict:
    """Las tres cifras y su cobertura, a partir de un puñado de filas."""
    salida = {
        "apropiacion": _suma(f[_I_APROP] for f in filas),
        "comprometido": _suma(f[_I_COMP] for f in filas),
        "girado": _suma(f[_I_GIRADO] for f in filas),
        "proyectado": _suma(f[_I_PROYECTADO] for f in filas),
    }
    vigencias = sorted({f[_I_VIGENCIA] for f in filas
                        if f[_I_APROP] is not None or f[_I_COMP] is not None
                        or f[_I_GIRADO] is not None})
    salida["cobertura"] = {
        "metas": len({f[_I_META] for f in filas}),
        "proyectos": len({f[_I_PROY_COD] for f in filas if f[_I_PROY_COD] is not None}),
        "vigencias": vigencias,
        "vigencia_desde": vigencias[0] if vigencias else None,
        "vigencia_hasta": vigencias[-1] if vigencias else None,
    }
    salida["fuente"] = "Matriz PDL · ALK"
    return salida


def _filtrar(filas, vigencia=None, proyectos=None, subgrupo_ids=None,
             programa_ids=None):
    """El único sitio donde se filtra. `proyectos` va por CÓDIGO normalizado
    («2780»), que es como la Matriz nombra al proyecto."""
    def pasa(f):
        if vigencia is not None and f[_I_VIGENCIA] != int(vigencia):
            return False
        if proyectos is not None and str(f[_I_PROY_COD]) not in proyectos:
            return False
        if subgrupo_ids is not None and f[_I_SUBGRUPO] not in subgrupo_ids:
            return False
        if programa_ids is not None and f[_I_PROGRAMA] not in programa_ids:
            return False
        return True

    return [f for f in filas if pasa(f)]


def _normalizar(codigos):
    """Los códigos de proyecto como los guarda la Matriz: sin ceros a la
    izquierda y como texto. `'0002780'`, `2780` y `'2780'` son el mismo."""
    if codigos is None:
        return None
    return {str(c).lstrip("0") or "0" for c in codigos}


# ─────────────────────────────────────────────────────────────────────
# La API pública. Todo lo que muestre plata del Plan pasa por acá.
# ─────────────────────────────────────────────────────────────────────

def plata(vigencia=None, proyectos=None, subgrupo_ids=None, programa_ids=None,
          cursor=None) -> dict:
    """Apropiación, comprometido, girado y proyectado del recorte pedido.

    Sin argumentos devuelve el total del Plan. Cada cifra puede venir en `None`
    —que significa «sin dato», nunca «cero pesos»— y viaja con la cobertura que
    la sostiene.
    """
    filas = _filtrar(_filas(cursor), vigencia, _normalizar(proyectos),
                     subgrupo_ids, programa_ids)
    return _acumular(filas)


def _por(indice, vigencia=None, cursor=None) -> dict:
    grupos: dict = {}
    for f in _filtrar(_filas(cursor), vigencia):
        clave = f[indice]
        if clave is None:
            continue
        grupos.setdefault(clave, []).append(f)
    return {k: _acumular(v) for k, v in grupos.items()}


def plata_por_proyecto(vigencia=None, cursor=None) -> dict:
    """{código de proyecto normalizado: cifras}. 30 de 30 proyectos."""
    return {str(k): v for k, v in _por(_I_PROY_COD, vigencia, cursor).items()}


def plata_por_subgrupo(vigencia=None, cursor=None) -> dict:
    """{subgrupo_id: cifras}. Las 16 áreas con plata en el Plan."""
    return _por(_I_SUBGRUPO, vigencia, cursor)


def plata_por_programa(vigencia=None, cursor=None) -> dict:
    """{programa_id: cifras}. Deja fuera las 8 filas sin programa (ver el
    encabezado): su plata sí está en el total y en el corte por proyecto."""
    return _por(_I_PROGRAMA, vigencia, cursor)


def plata_por_sector(vigencia=None, cursor=None) -> dict:
    """{nombre oficial del sector: cifras}."""
    return _por(_I_SECTOR, vigencia, cursor)


def proyecto_id_por_codigo(cursor=None) -> dict:
    """{código normalizado: id interno del proyecto}. Para que quien tenga ids
    no tenga que volver a cruzar por su cuenta."""
    return {str(f[_I_PROY_COD]): f[_I_PROY_ID]
            for f in _filas(cursor)
            if f[_I_PROY_COD] is not None and f[_I_PROY_ID] is not None}


# ─────────────────────────────────────────────────────────────────────
# El CONTRASTE. Nunca entra al cálculo: va al lado.
# ─────────────────────────────────────────────────────────────────────
#
# Regla de Alex (2026-09-10): «una sola fuente para los indicadores, y las
# demás como referencia al lado». El contraste vive acá, junto a la cifra
# oficial, por una razón concreta: si cada pantalla arma su propia comparación,
# en seis meses hay tantas versiones del contraste como del dato.
#
# QUÉ SE PUEDE CONTRASTAR Y QUÉ NO. BogData llega hasta el PROYECTO —por el
# rubro, por el elemento del Plan o, como respaldo, por el contrato cuando ese
# contrato está en innovaK— y ahí se detiene. NO baja a la meta. Así que la
# comparación existe por proyecto y por los totales, y **no puede existir por
# meta ni por indicador**: pedirla ahí no es difícil, es imposible con las
# fuentes que hay.

def contraste_bogdata(proyecto_ids=None) -> dict:
    """{proyecto_id: {comprometido, girado, anterior_al_pdl, filas}}.

    EL CORTE ES EL AÑO DEL COMPROMISO, y el criterio no se reimplementa acá:
    sale de `metrics.del_pdl`, que es su única definición. De los $135.078 M de
    obligaciones por pagar, $93.209 M son de compromisos de 2025 —dentro del
    Plan— así que cortar por `es_obligacion_por_pagar` se los llevaría junto
    con lo viejo.
    """
    from django.db.models import Count, Sum

    from apps.presupuesto.models.sql import Crp
    from apps.presupuesto.services.metrics import (VIGENCIA_INICIAL_PDL,
                                                   del_pdl)

    def _agregar(qs):
        filas = (qs.exclude(proyecto_id__isnull=True)
                   .values("proyecto_id")
                   .annotate(neto=Sum("valor_neto"),
                             girado=Sum("autorizacion_giro"),
                             n=Count("id")))
        return {f["proyecto_id"]: f for f in filas}

    base = Crp.objects.filter(vigente=True)
    if proyecto_ids is not None:
        base = base.filter(proyecto_id__in=proyecto_ids)

    del_plan = _agregar(del_pdl(base))
    anteriores = _agregar(base.filter(compromiso_anio__lt=VIGENCIA_INICIAL_PDL))

    salida: dict = {}
    for pid in set(del_plan) | set(anteriores):
        d, a = del_plan.get(pid), anteriores.get(pid)
        salida[pid] = {
            "comprometido": float(d["neto"]) if d and d["neto"] is not None else None,
            "girado": float(d["girado"]) if d and d["girado"] is not None else None,
            "anterior_al_pdl": float(a["neto"]) if a and a["neto"] is not None else None,
            "filas": (d["n"] if d else 0) + (a["n"] if a else 0),
            "fuente": "BogData · CRP",
        }
    return salida


def _cortes(cursor) -> dict:
    """De cuándo es cada fuente. Sin esto, dos cifras de fechas distintas se
    leen como si fueran del mismo día."""
    from apps.presupuesto.services.muro_subgrupos import _corte_matriz_pdl

    cursor.execute("SELECT MAX(fecha_corte) FROM crp_carga")
    corte_crp = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(synced_at) FROM secop_contrato")
    corte_secop = cursor.fetchone()[0]
    return {
        "matriz": _corte_matriz_pdl(cursor),
        "bogdata": corte_crp.isoformat() if corte_crp else None,
        "secop": corte_secop.isoformat() if corte_secop else None,
    }


def contraste(vigencia=None) -> dict:
    """La comparación completa, proyecto por proyecto, para la pestaña nueva.

    LO QUE MANDA VA PRIMERO. `oficial` es la Matriz: es la cifra que el sistema
    publica. `bogdata` va al lado con su propia fecha de corte y su propio
    universo, y la diferencia se calcula pero NO se interpreta — no está
    conciliada, y decidir de qué lado está la explicación sin haberlo medido
    es exactamente lo que este módulo evita.

    La diferencia global medida el 2026-09-10 son $40.014.478.670 sobre un
    comprometido de $224.853.665.855: no es ruido de redondeo, es una pregunta
    abierta para la Alcaldía y para Hacienda.
    """
    from django.db import connection

    with connection.cursor() as cur:
        filas = _filas(cur)
        por_proyecto = plata_por_proyecto(vigencia, cur)
        ids = proyecto_id_por_codigo(cur)
        cortes = _cortes(cur)
        cur.execute("SELECT id, codigo, nombre FROM proyecto")
        nombres = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    bog = contraste_bogdata()

    items = []
    for codigo, oficial in sorted(por_proyecto.items()):
        pid = ids.get(codigo)
        b = bog.get(pid, {})
        comp_of, comp_bo = oficial["comprometido"], b.get("comprometido")
        items.append({
            "proyecto_codigo": codigo,
            "proyecto_id": pid,
            "proyecto": nombres.get(pid, (None, None))[1],
            "oficial": oficial,
            "bogdata": b or None,
            # `None` cuando falta cualquiera de los dos lados: una resta con un
            # vacío no da cero, da nada.
            "diferencia": (comp_of - comp_bo
                           if comp_of is not None and comp_bo is not None else None),
        })

    # ── LOS TOTALES NO SON LA SUMA DE LAS FILAS DE ARRIBA, Y ESO HAY QUE
    #    DECIRLO. BogData atribuye a un proyecto solo una parte de su plata:
    #    medido el 2026-09-10, $86.603.918.854 de los $184.839.187.185 del
    #    Plan (47 %). Los $98.235.268.331 restantes son 1.178 filas sin
    #    proyecto, y $92.160.547.878 de ellas son «Obligaciones por pagar
    #    Inversión vigencia anterior», cuyo rubro no identifica proyecto.
    #
    #    Si el total se sumara de las filas visibles, la diferencia contra la
    #    Matriz saldría $138.249 M en vez de $40.014 M, y ese exceso no sería
    #    un desacuerdo: sería plata que BogData no alcanza a atribuir. Es
    #    exactamente el error que este módulo existe para no cometer.
    from apps.presupuesto.services.metrics import (_comprometido_antes_del_pdl,
                                                   _comprometido_crp)

    total_of = _acumular(_filtrar(filas, vigencia))
    atribuido = _suma(v.get("comprometido") for v in bog.values())
    comprometido_bo = float(_comprometido_crp())
    total_bo = {
        "comprometido": comprometido_bo,
        "girado": _suma(v.get("girado") for v in bog.values()),
        "atribuido_a_proyecto": atribuido,
        "sin_proyecto": (comprometido_bo - atribuido
                         if atribuido is not None else None),
        "cobertura_pct": (round(atribuido / comprometido_bo * 100, 1)
                          if atribuido and comprometido_bo else None),
        "anterior_al_pdl": float(_comprometido_antes_del_pdl()),
        "fuente": "BogData · CRP",
    }
    dif = (total_of["comprometido"] - total_bo["comprometido"]
           if total_of["comprometido"] is not None
           and total_bo["comprometido"] is not None else None)

    return {
        "vigencia": int(vigencia) if vigencia else None,
        "items": items,
        "totales": {"oficial": total_of, "bogdata": total_bo, "diferencia": dif},
        "cortes": cortes,
        "nota_alcance": (
            "BogData atribuye la plata al proyecto, no a la meta: la "
            "comparación existe por proyecto y por totales, no por meta. "
            "Y no toda su plata llega al proyecto: las obligaciones por pagar "
            "de vigencias anteriores traen un rubro que no lo identifica, así "
            "que las filas de esta tabla suman menos que el total."),
    }
