"""Los contratos de Kennedy, preparados para publicarse.

## Qué publica y qué NO

La fuente es el espejo de SECOP II (`secop_contrato`), enriquecido con el plan
de pagos (`secop_plan_pago`, que cubre ~95 % de los contratos), las
modificaciones (`secop_modificacion`) y, cuando existe, el enganche con el Plan
de Desarrollo Local.

**El alcance es 2024 en adelante**, que es el del Plan vigente. La ingesta trae
ese corte por defecto; correrla sin el flag llegó a meter 3.028 contratos de
2017-2023 y a triplicar el universo de la API sin que se notara, porque solo
cambió un número.

### Datos personales — la regla, y quién la decidió

Contratistas persona natural son la mayoría de los contratos, y su documento es
una cédula. **Se publican nombre y documento por decisión de la Alcaldía**
(Alex, 2026-09-21): «los datos son públicos… por eso traemos desde datos
abiertos, somos servidores públicos».

Es la lectura legal correcta: la Ley 1712 hace pública la contratación estatal,
el dato entra a este sistema DESDE el portal de datos abiertos del Distrito, y
republicarlo con el alcance de Kennedy ya filtrado es el servicio que presta
esta API. La decisión de oportunidad le corresponde a la Alcaldía, no a este
archivo.

Sigue siendo reversible sin tocar código, y por eso los interruptores no se
quitaron:

    PUBLICA_DOCUMENTO_NATURALES=0    cierra el número de documento
    PUBLICA_NOMBRE_NATURALES=0       cierra el nombre

Con ellos cerrados, las personas jurídicas siguen saliendo completas (un NIT no
es dato personal) y las naturales viajan solo con `proveedor_ref`.

`proveedor_ref` se conserva aunque el documento sea público: es un HMAC
truncado con sal del servidor, y agrupar por él es más cómodo que por una
cadena que el origen escribe con espacios y puntos.

### `valor_pagado`: el cero que miente

`secop_contrato` no tiene UNA sola fila con `valor_pagado` en NULL: el 0 y el
«no se reportó» son indistinguibles por construcción. Y varios de esos ceros
tienen giro probado en BogData — el caso claro es CIA-773-2025, que marca $0 en
SECOP mientras BogData registra $8.818.769.452 autorizados.

Publicar `valor_pagado: 0` como cifra oficial de gasto público sería afirmar
que no se pagó algo que sí se pagó. Por eso un 0 sale como `null` con su
motivo, y nunca como cero.

### La identidad del recurso

`id_contrato` (`CO1.PCCNTR.7876249`), que es el identificador de SECOP: único
en el espejo, con índice único en la tabla, estable entre sincronizaciones
porque el upsert busca por él, y verificable contra datos.gov.co.
**`referencia_contrato` NO sirve**: se repite (CPS-134-2024 y CPS-653-2024
están dos veces).

### El enganche con el Plan

Es lo único que Kennedy tiene y SECOP no. Hoy cubre poco y se publica igual,
con el vacío a la vista y la cobertura medida en `/metadatos/`: unas pocas
decenas llegan al expediente interno, menos a una actividad del plan y
**ninguna a una meta**. No es el titular de esta API; es la promesa que se ve
crecer, y tenerla visible es presión sana para llenarla.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import connection

from apps.publico.services import modificaciones as _mods
from apps.publico.services import referencia as _ref_parse

#: Los dos interruptores de datos personales. Ver el docstring del módulo.
#: Se leen de settings para que abrirlos sea un cambio explícito y revisable.
DOCUMENTO_NATURALES = getattr(settings, "PUBLICA_DOCUMENTO_NATURALES", False)
NOMBRE_NATURALES = getattr(settings, "PUBLICA_NOMBRE_NATURALES", False)

#: Sal del seudónimo. Si cambia, los `proveedor_ref` publicados cambian y un
#: consumidor pierde la capacidad de agrupar históricos: no se rota a la
#: ligera.
_SAL = getattr(settings, "PUBLICA_SAL_PROVEEDOR", None) or settings.SECRET_KEY

MOTIVO_PAGADO_CERO = (
    "SECOP reporta 0 y no distingue «no se giró» de «no se reportó»: la tabla "
    "no tiene un solo valor nulo en esta columna. Consulte el plan de pagos "
    "del contrato o el registro presupuestal."
)
MOTIVO_SIN_PLAN = (
    "Este contrato todavía no está conciliado con el expediente interno de la "
    "Alcaldía. La cobertura del enganche con el Plan es del 0,8 %."
)

#: Un contrato puede tener varias filas de tercero por documentos repetidos en
#: el catálogo de BogData (3 documentos, 11 contratos). LATERAL … LIMIT 1 para
#: que el join no multiplique filas: con el join plano la lista devolvía 3.163
#: contratos donde hay 3.152.
_TERCERO = """
LEFT JOIN LATERAL (
  SELECT tt.es_juridica
  FROM tercero_sap tt
  WHERE regexp_replace(tt.num_doc, '[^0-9]', '', 'g')
      = regexp_replace(COALESCE(s.documento_proveedor,''), '[^0-9]', '', 'g')
    AND regexp_replace(COALESCE(s.documento_proveedor,''), '[^0-9]', '', 'g') <> ''
  ORDER BY (tt.es_juridica IS NULL), tt.id
  LIMIT 1
) t ON TRUE"""

_NATURALEZA = """
CASE
  WHEN t.es_juridica IS TRUE  THEN 'juridica'
  WHEN t.es_juridica IS FALSE THEN 'natural'
  WHEN length(regexp_replace(COALESCE(s.documento_proveedor,''), '[^0-9]', '', 'g')) = 9
       AND left(regexp_replace(COALESCE(s.documento_proveedor,''), '[^0-9]', '', 'g'), 1)
           IN ('8','9') THEN 'juridica'
  WHEN regexp_replace(COALESCE(s.documento_proveedor,''), '[^0-9]', '', 'g') <> ''
       THEN 'natural'
  ELSE NULL
END"""

_CAMPOS = """
    s.id_contrato, s.referencia_contrato, s.proceso_de_compra, s.anio,
    s.estado_contrato, s.tipo_contrato, s.modalidad,
    s.objeto_contrato, s.descripcion_proceso,
    s.valor_contrato, s.valor_pagado, s.valor_pendiente_ejec, s.saldo_cdp,
    s.fecha_firma, s.fecha_inicio, s.fecha_fin,
    s.url_proceso, s.nombre_entidad, s.nit_entidad,
    s.proveedor, s.documento_proveedor, s.synced_at,
    s.dias_adicionados, s.duracion_contrato, s.tipo_doc_proveedor,
""" + _NATURALEZA + " AS naturaleza"

#: Orden por el que se pagina. Es el identificador único y estable, así que el
#: cursor no se desfasa cuando la sincronización inserta filas entre dos
#: páginas — que es el problema real del offset.
_ORDEN = "ORDER BY s.id_contrato"


def _ref(documento: str | None) -> str | None:
    """Seudónimo estable del proveedor. Agrupa sin revelar el número."""
    doc = "".join(ch for ch in (documento or "") if ch.isdigit())
    if not doc:
        return None
    return hmac.new(str(_SAL).encode(), doc.encode(), hashlib.sha256).hexdigest()[:16]


def _f(v):
    return None if v is None else float(v)


def _iso(d):
    return d.isoformat() if d else None


def _fin_inicial(fin, dias_adicionados):
    """La fecha de fin ANTES de las prórrogas.

    `fin − dias_adicionados`. No es una estimación: los días adicionados los
    publica SECOP. Si no hay días adicionados el contrato no se prorrogó, así
    que la inicial y la actual son la misma fecha — y eso es un dato, no un
    hueco.
    """
    if not fin:
        return None
    if not dias_adicionados:
        return fin
    return fin - timedelta(days=int(dias_adicionados))


def _proveedor(nombre, documento, naturaleza, tipo_doc=None) -> dict:
    """El bloque del proveedor. Ver «datos personales» en el docstring."""
    es_juridica = naturaleza == "juridica"
    bloque = {
        "naturaleza": naturaleza,
        # El TIPO de documento viaja siempre. Es lo que pidió el equipo para
        # poder asociar un contrato a una persona: un número sin su tipo no
        # identifica, y el tipo por sí solo tampoco.
        "tipo_documento": tipo_doc or None,
        "proveedor_ref": _ref(documento),
    }
    if es_juridica or NOMBRE_NATURALES:
        bloque["nombre"] = nombre or None
    else:
        bloque["nombre"] = None
        bloque["nombre_motivo"] = (
            "No se publica el nombre de contratistas persona natural.")
    if es_juridica or DOCUMENTO_NATURALES:
        bloque["documento"] = documento or None
    else:
        bloque["documento"] = None
        bloque["documento_motivo"] = (
            "No se publica el documento de contratistas persona natural. "
            "Use `proveedor_ref` para agrupar los contratos de un mismo "
            "proveedor.")
    return bloque


def _fila(r: tuple, plan_por_contrato: dict, enganche: dict,
          mods_por_contrato: dict | None = None) -> dict:
    (id_ct, ref, proceso, anio, estado, tipo, modalidad, objeto, descripcion,
     valor, pagado, pendiente, saldo_cdp, firma, inicio, fin, url, entidad,
     nit, proveedor, documento, synced, dias_adic, duracion, tipo_doc,
     naturaleza) = r

    pagado_f = _f(pagado)
    # EL CERO QUE MIENTE. Ver el docstring del módulo.
    pagado_publicable = None if (pagado_f is None or pagado_f == 0) else pagado_f

    plan = enganche.get(id_ct)
    mods = (mods_por_contrato or {}).get(id_ct) if mods_por_contrato is not None else None
    if mods_por_contrato is not None and mods is None:
        mods = []
    return {
        "id_contrato": id_ct,
        "referencia_contrato": ref,
        # La referencia partida en sus pedazos, con el código de SIPSE aparte.
        # `parseo` dice si hubo que corregirla: el origen viene sucio y no se
        # corrige en silencio. Ver services/referencia.py.
        "referencia": _ref_parse.parsear(ref),
        "proceso_de_compra": proceso,
        "anio": anio,
        "estado": estado,
        "tipo": tipo,
        "modalidad": modalidad,
        "objeto": objeto,
        "descripcion_proceso": descripcion,
        "entidad": {"nombre": entidad, "nit": nit},
        "proveedor": _proveedor(proveedor, documento, naturaleza, tipo_doc),
        "valores": {
            "moneda": "COP",
            "valor_contrato": _f(valor),
            "valor_pagado": pagado_publicable,
            "valor_pagado_motivo": (MOTIVO_PAGADO_CERO
                                    if pagado_publicable is None else None),
            "valor_pendiente_ejec": _f(pendiente),
            # 252 filas traen `saldo_cdp` mayor que el valor del contrato y
            # 2.566 vienen en cero: se publica, marcado como no fiable, en vez
            # de esconderlo o de presentarlo como si cuadrara.
            "saldo_cdp": _f(saldo_cdp),
            "saldo_cdp_confiable": False,
        },
        # LAS FECHAS, SEPARADAS. `fin` es la vigente; la INICIAL se obtiene
        # restándole los días adicionados, que es dato de SECOP y no una
        # estimación nuestra. Si no hay días adicionados, la inicial es la
        # misma que la actual y se dice, en vez de dejar el campo vacío.
        "fechas": {
            "firma": _iso(firma),
            "inicio": _iso(inicio),
            "fin_actual": _iso(fin),
            "fin_inicial": _iso(_fin_inicial(fin, dias_adic)),
            "fin_inicial_motivo": (
                None if fin else
                "El contrato no tiene fecha de fin registrada en SECOP."),
            "dias_adicionados": dias_adic,
            "duracion_contrato": duracion,
            # Se conserva el nombre viejo para no romper a quien ya consume.
            "fin": _iso(fin),
        },
        "modificaciones": _mods.resumen(mods) if mods is not None else None,
        "plan_pagos": plan_por_contrato.get(id_ct),
        "plan_desarrollo": plan,
        "plan_desarrollo_motivo": None if plan else MOTIVO_SIN_PLAN,
        "fuente": {
            "sistema": "SECOP II",
            "dataset": "jbjy-vk9h",
            "url_proceso": url,
            "verificado_en": _iso(synced),
        },
    }


def _plan_pagos(cur, ids: list[str]) -> dict:
    """Resumen del plan de pagos por contrato. Agregado, no fila por fila."""
    if not ids:
        return {}
    cur.execute("""
        SELECT id_del_contrato, COUNT(*),
               COALESCE(SUM(valor_total), 0),
               COUNT(*) FILTER (WHERE fecha_real_de_pago IS NOT NULL)
        FROM secop_plan_pago
        WHERE id_del_contrato = ANY(%s)
        GROUP BY id_del_contrato
    """, [ids])
    return {cid: {"registros": int(n or 0),
                  "valor_total": _f(total),
                  "con_pago_real": int(pagados or 0)}
            for cid, n, total, pagados in cur.fetchall()}


def _enganche_plan(cur, ids: list[str]) -> dict:
    """A qué proyecto, área y actividad del Plan llega cada contrato."""
    if not ids:
        return {}
    cur.execute("""
        SELECT s.id_contrato, p.codigo, p.nombre, sg.nombre, ap.descripcion
        FROM secop_contrato s
        JOIN contrato ct
          ON upper(trim(s.referencia_contrato)) ~
             ('(^|[^0-9])' || ct.contrato_numero || '[^0-9]+' || ct.contrato_vigencia)
        LEFT JOIN contrato_proyecto cp ON cp.contrato_id = ct.id
        LEFT JOIN proyecto p           ON p.id = cp.proyecto_id
        LEFT JOIN subgrupo sg          ON sg.id = p.subgrupo_id
        LEFT JOIN contrato_actividad_plan cap ON cap.contrato_id = ct.id AND cap.activo
        LEFT JOIN actividad_plan ap    ON ap.id = cap.actividad_plan_id
        WHERE s.id_contrato = ANY(%s)
    """, [ids])
    salida = {}
    for cid, proy_cod, proy_nom, area, actividad in cur.fetchall():
        if cid in salida:
            continue
        salida[cid] = {
            "proyecto_codigo": proy_cod,
            "proyecto_nombre": proy_nom,
            "area": area,
            "actividad": actividad,
            # `null` con su motivo, nunca un objeto de ceros.
            "meta": None,
            "meta_motivo": ("La vinculación contrato→meta no está poblada: las "
                            "15 filas de `contrato_actividad_plan` tienen la "
                            "meta en nulo."),
        }
    return salida


FILTROS = {
    "anio": "s.anio = %s",
    "estado": "s.estado_contrato = %s",
    "tipo": "s.tipo_contrato = %s",
    "modalidad": "s.modalidad = %s",
    "valor_min": "s.valor_contrato >= %s",
    "valor_max": "s.valor_contrato <= %s",
    "firma_desde": "s.fecha_firma >= %s",
    "firma_hasta": "s.fecha_firma <= %s",
    # SINCRONIZACIÓN INCREMENTAL. Quien ya bajó el dataset no tiene por qué
    # volver a bajarlo entero: pide lo que cambió desde su último corte.
    #
    # Ojo con qué significa: `synced_at` se mueve cuando la fila CAMBIA, así
    # que esto trae «lo que la ingesta modificó desde entonces», que es
    # justo lo que sirve para actualizar una copia. No es «contratos firmados
    # desde», que es `firma_desde`.
    "actualizado_desde": "s.synced_at >= %s",
}

#: Parámetros que NO son filtros pero sí son válidos en la petición.
_NO_FILTRO = {"cursor", "limite", "formato", "format"}

#: Los que sí filtran pero no viven en FILTROS porque su SQL es especial.
_FILTRO_ESPECIAL = {"q", "naturaleza"}

PARAMETROS_VALIDOS = set(FILTROS) | _FILTRO_ESPECIAL | _NO_FILTRO


class ParametroDesconocido(ValueError):
    """Un parámetro que la API no entiende. Se responde 400, no 200.

    Ignorarlo en silencio es peor que rechazarlo: `?anoo=2025` devolvía los
    3.169 contratos con un 200 y cara de haber filtrado. Quien consume no
    tiene cómo notar la diferencia entre «ese año tiene todo el dataset» y
    «escribiste mal el parámetro», y termina publicando un total que no es.
    """

    def __init__(self, desconocidos: list[str]):
        self.desconocidos = sorted(desconocidos)
        super().__init__(
            "Parámetros que esta API no reconoce: "
            + ", ".join(self.desconocidos)
            + ". Válidos: " + ", ".join(sorted(PARAMETROS_VALIDOS)) + ".")


def validar_parametros(recibidos) -> None:
    """Rechaza lo que no se entiende. Llamar ANTES de construir el WHERE."""
    desconocidos = [p for p in recibidos if p not in PARAMETROS_VALIDOS]
    if desconocidos:
        raise ParametroDesconocido(desconocidos)


def _where(filtros: dict, cursor_id: str | None) -> tuple[str, list]:
    partes, params = [], []
    for clave, sql in FILTROS.items():
        valor = filtros.get(clave)
        if valor not in (None, ""):
            partes.append(sql)
            params.append(valor)
    if filtros.get("q"):
        partes.append("(s.objeto_contrato ILIKE %s OR s.referencia_contrato ILIKE %s)")
        params += [f"%{filtros['q']}%"] * 2
    if filtros.get("naturaleza"):
        partes.append(f"({_NATURALEZA}) = %s")
        params.append(filtros["naturaleza"])
    if cursor_id:
        partes.append("s.id_contrato > %s")
        params.append(cursor_id)
    return ("WHERE " + " AND ".join(partes)) if partes else "", params


def listar(filtros: dict | None = None, cursor_id=None, limite=50) -> dict:
    """Una página de contratos. Paginación por cursor sobre `id_contrato`."""
    filtros = filtros or {}
    limite = max(1, min(int(limite or 50), 500))
    where, params = _where(filtros, cursor_id)

    with connection.cursor() as cur:
        cur.execute(
            f"SELECT {_CAMPOS} FROM secop_contrato s {_TERCERO} {where} "
            f"{_ORDEN} LIMIT %s", params + [limite + 1])
        filas = cur.fetchall()
        hay_mas = len(filas) > limite
        filas = filas[:limite]
        ids = [f[0] for f in filas]
        planes = _plan_pagos(cur, ids)
        enganches = _enganche_plan(cur, ids)

        where_total, params_total = _where(filtros, None)
        cur.execute(
            f"SELECT COUNT(*) FROM secop_contrato s {_TERCERO} {where_total}",
            params_total)
        total = int(cur.fetchone()[0] or 0)

    # En la lista va el RESUMEN de modificaciones, no la lista entera: son
    # 4.304 filas y meterlas todas haría la página inservible. El detalle
    # completo está en /contratos/{id}/modificaciones/.
    mods = _mods.por_contrato(ids)

    return {
        "count": total,
        "next_cursor": (filas[-1][0] if hay_mas and filas else None),
        "results": [_fila(f, planes, enganches, mods) for f in filas],
    }


def detalle(id_contrato: str) -> dict | None:
    """Un contrato por su identificador de SECOP.

    Un identificador con barra no existe: la ruta usa `path:`, que sí captura
    barras, así que `…/algo-que-no-es-una-ruta` llegaría acá entero.
    """
    if not id_contrato or "/" in id_contrato:
        return None
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT {_CAMPOS} FROM secop_contrato s {_TERCERO} "
            f"WHERE s.id_contrato = %s", [id_contrato])
        fila = cur.fetchone()
        if not fila:
            return None
        planes = _plan_pagos(cur, [fila[0]])
        enganches = _enganche_plan(cur, [fila[0]])
    mods = _mods.por_contrato([fila[0]])
    return _fila(fila, planes, enganches, mods)
