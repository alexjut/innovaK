"""Los contratos de Kennedy, preparados para publicarse.

## Qué publica y qué NO

La fuente es el espejo de SECOP II (`secop_contrato`, 3.152 filas de la
ALCALDIA LOCAL DE KENNEDY), enriquecido con el plan de pagos (`secop_plan_pago`,
36.626 filas que cubren el 95,5 % de los contratos) y, cuando existe, el
enganche con el Plan de Desarrollo Local.

### Datos personales — la regla, y por qué

**3.051 de los 3.152 contratos son de persona natural** y hay ~1.400 documentos
distintos: publicar `documento_proveedor` en bruto es entregar un padrón de
cédulas agrupable con una sola consulta. La contratación estatal es pública por
la Ley 1712 y SECOP ya la publica, pero *estar disponible* y *ser entregado en
bloque y filtrable* no son lo mismo, y el riesgo de reidentificación recae
sobre la Alcaldía.

Por eso, por defecto:

  · el documento sale COMPLETO solo para personas jurídicas (es un NIT, y un
    NIT no es dato personal);
  · para personas naturales sale `proveedor_ref`, un HMAC truncado con sal del
    servidor. Permite AGRUPAR los contratos de un mismo proveedor —que es el
    uso analítico real— sin revelar el número.

Las dos decisiones que faltan son de un humano y están aisladas en dos ajustes,
para que abrirlas sea explícito y quede en el historial:

    PUBLICA_DOCUMENTO_NATURALES = False   # el número de cédula
    PUBLICA_NOMBRE_NATURALES    = False   # el nombre del contratista

El nombre del contratista del Estado es legalmente público. Sigue en `False`
por defecto porque la decisión de oportunidad —y el visto bueno jurídico— le
corresponden a la Alcaldía, no a este archivo.

### `valor_pagado`: el cero que miente

`secop_contrato` tiene **209 filas con `valor_pagado = 0` y CERO filas en
NULL**: el 0 y el «no se reportó» son indistinguibles por construcción. De esos
209, **5 tienen giro probado en BogData** — el caso claro es CIA-773-2025, que
marca $0 en SECOP mientras BogData registra $8.818.769.452 autorizados.

Publicar `valor_pagado: 0` como cifra oficial de gasto público sería afirmar
que no se pagó algo que sí se pagó. Por eso un 0 sale como `null` con su
motivo, y nunca como cero.

### La identidad del recurso

`id_contrato` (`CO1.PCCNTR.7876249`), que es el identificador de SECOP: único
en las 3.152 filas, con índice único en la tabla, estable entre
sincronizaciones porque el upsert busca por él, y verificable contra
datos.gov.co. **`referencia_contrato` NO sirve**: se repite (CPS-134-2024 y
CPS-653-2024 están dos veces).

### El enganche con el Plan

Es lo único que Kennedy tiene y SECOP no. Hoy cubre poco y se publica igual,
con el vacío a la vista: 24 de 3.152 llegan al expediente interno (0,76 %), 5 a
una actividad del plan (0,16 %) y **ninguno a una meta**. No es el titular de
esta API; es la promesa que se ve crecer.
"""
from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.db import connection

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


def _proveedor(nombre, documento, naturaleza) -> dict:
    """El bloque del proveedor, ya filtrado. Ver «datos personales» arriba."""
    es_juridica = naturaleza == "juridica"
    bloque = {
        "naturaleza": naturaleza,
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


def _fila(r: tuple, plan_por_contrato: dict, enganche: dict) -> dict:
    (id_ct, ref, proceso, anio, estado, tipo, modalidad, objeto, descripcion,
     valor, pagado, pendiente, saldo_cdp, firma, inicio, fin, url, entidad,
     nit, proveedor, documento, synced, naturaleza) = r

    pagado_f = _f(pagado)
    # EL CERO QUE MIENTE. Ver el docstring del módulo.
    pagado_publicable = None if (pagado_f is None or pagado_f == 0) else pagado_f

    plan = enganche.get(id_ct)
    return {
        "id_contrato": id_ct,
        "referencia_contrato": ref,
        "proceso_de_compra": proceso,
        "anio": anio,
        "estado": estado,
        "tipo": tipo,
        "modalidad": modalidad,
        "objeto": objeto,
        "descripcion_proceso": descripcion,
        "entidad": {"nombre": entidad, "nit": nit},
        "proveedor": _proveedor(proveedor, documento, naturaleza),
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
        "fechas": {"firma": _iso(firma), "inicio": _iso(inicio), "fin": _iso(fin)},
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
}


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

    return {
        "count": total,
        "next_cursor": (filas[-1][0] if hay_mas and filas else None),
        "results": [_fila(f, planes, enganches) for f in filas],
    }


def detalle(id_contrato: str) -> dict | None:
    """Un contrato por su identificador de SECOP."""
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT {_CAMPOS} FROM secop_contrato s {_TERCERO} "
            f"WHERE s.id_contrato = %s", [id_contrato])
        fila = cur.fetchone()
        if not fila:
            return None
        planes = _plan_pagos(cur, [fila[0]])
        enganches = _enganche_plan(cur, [fila[0]])
    return _fila(fila, planes, enganches)
