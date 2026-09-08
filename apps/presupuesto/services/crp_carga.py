"""Cargar el reporte de CRP de BogData. Idempotente, y con un gate que aborta.

CÓMO SE LEE ESTE ARCHIVO. Una fila del reporte es una POSICIÓN de CRP, no un
contrato. Las 2.630 filas del corte 2026-09-07 son 2.265 compromisos: un
contrato aparece varias veces por adiciones, por obligaciones por pagar de
vigencias anteriores registradas por fracciones, o simplemente por tener más
de una posición.

LOS VALORES SON SALDOS, NO MOVIMIENTOS. `valor_crp`, `anulaciones`, `girado` y
los demás vienen acumulados al corte. Cada carga REEMPLAZA el estado de la
fila (upsert por la PK natural); sumarlos sobre lo anterior duplicaría la
plata de la localidad. Es la diferencia entre un extracto y una factura.

LO QUE DESAPARECE NO SE BORRA. Si un (interno, posición) deja de venir en un
corte nuevo, se marca `vigente=False`. Un DELETE perdería la respuesta a
«¿desde cuándo dejó de estar?», que es lo que se pregunta cuando alguien
reclama por una anulación.

EL GATE. Si los seis totales no cuadran con el archivo, la carga ABORTA sin
escribir. No es celo: un reporte truncado a la mitad se ve igual de bien fila
por fila, y entra sin que nadie lo note hasta que las cifras del tablero no
cuadran con las de la Secretaría.
"""
from __future__ import annotations

import os
from decimal import Decimal

from django.db import transaction

from apps.presupuesto.services.crp_normalizar import (
    es_persona_juridica, normalizar_numero_compromiso, proyecto_de_pep,
    proyecto_de_rubro, tipo_de_rubro,
)

HOJA = "Data"

#: Columna del Excel → clave interna. Las que el diccionario marca como
#: constantes o vacías (Grafo, Producto PMR, Forma Pago…) no se leen: guardar
#: una columna que siempre dice lo mismo es ruido que alguien va a tener que
#: descartar más adelante.
COLUMNAS = {
    "Ejercicio": "vigencia",
    "Período": "periodo",
    "Fecha Registro": "fecha_registro",
    "Tipo de compromiso": "tipo_compromiso_cod",
    "Compromiso": "tipo_compromiso_desc",
    "No. Compromiso": "compromiso_raw",
    "Plazo (Días)": "plazo_dias",
    "Número de CDP": "numero_cdp",
    "Número de CRP": "numero_crp",
    "Objeto": "objeto",
    "Rubro": "rubro",
    "Descripción del Rubro": "rubro_desc",
    "Fondos": "fondo_cod",
    "Descripcion del Fondo": "fondo_desc",
    "Cod.Concepto Gasto": "concepto_gasto_cod",
    "Decripción Concepto Gasto": "concepto_gasto_desc",
    "Elemento PEP": "elemento_pep",
    "Texto Id Proyecto": "texto_id_proyecto",
    "Modalidad de selección": "modalidad_cod",
    "Descripcion Mod. Selec": "modalidad_desc",
    "BP Beneficiario": "bp_sap",
    "Tipo Doc. BP Beneficiario": "tipo_doc",
    "Número Doc. BP Beneficiario": "num_doc",
    "Nombre BP Beneficiario": "tercero_nombre",
    "ID Responsable": "responsable_id",
    "Reponsable": "responsable_nombre",     # (sic) viene con typo en la fuente
    "ID Solicitante": "solicitante_id",
    "Nombre Solicitante": "solicitante_nombre",
    "Valor CRP": "valor_crp",
    "Anulaciones": "anulaciones",
    "Reintegros": "reintegros",
    "Valor Neto": "valor_neto",
    "Autorizacion giro": "autorizacion_giro",
    "Com.Sin.Aut.Giro": "sin_autorizacion_giro",
    "N° Interno CRP": "interno_crp",
    "N° Posición CRP": "posicion_crp",
    "N° Interno CDP": "interno_cdp",
    "N° Posición CDP": "posicion_cdp",
    "Fecha de entrada": "fecha_entrada",
    "Programa Financiamiento": "programa_financiamiento",
}

#: Las repetidas. pandas las vería como `Fecha Inicial.1`; con openpyxl hay
#: que pedirlas por ocurrencia. Las PRIMERAS son el rango del reporte; las
#: SEGUNDAS, las fechas del compromiso — confundirlas pondría a todos los
#: contratos empezando el mismo día.
COL_REPETIDAS = {
    ("Fecha Inicial", 0): "reporte_desde",
    ("Fecha Final", 0): "reporte_hasta",
    ("Fecha Inicial", 1): "fecha_inicio_compromiso",
    ("Fecha Final", 1): "fecha_fin_compromiso",
}

CAMPOS_PLATA = ("valor_crp", "anulaciones", "reintegros", "valor_neto",
                "autorizacion_giro", "sin_autorizacion_giro")

MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo",
         6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre",
         10: "Octubre", 11: "Noviembre", 12: "Diciembre"}


class CargaError(Exception):
    """Algo impide seguir. El mensaje va tal cual a la pantalla."""


def _int(v):
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _fecha(v):
    if v is None:
        return None
    return v.date() if hasattr(v, "date") else v


def leer(ruta) -> list[dict]:
    """El archivo a una lista de diccionarios, ya con los tipos resueltos."""
    import openpyxl

    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    if HOJA not in wb.sheetnames:
        raise CargaError(
            f"El Excel no tiene la hoja «{HOJA}». ¿Es el reporte de CRP de "
            f"BogData y no otro archivo?")
    ws = wb[HOJA]
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))

    idx = {}
    for col, clave in COLUMNAS.items():
        pos = [i for i, h in enumerate(hdr) if h == col]
        if not pos:
            raise CargaError(
                f"Falta la columna «{col}». El reporte cambió de formato: "
                f"revisar el diccionario antes de cargar.")
        idx[clave] = pos[0]
    for (col, k), clave in COL_REPETIDAS.items():
        pos = [i for i, h in enumerate(hdr) if h == col]
        if len(pos) <= k:
            raise CargaError(f"Falta la ocurrencia {k + 1} de la columna «{col}».")
        idx[clave] = pos[k]

    filas = []
    for fila in it:
        if fila is None or all(v is None for v in fila):
            continue
        d = {clave: fila[pos] for clave, pos in idx.items()}
        for c in CAMPOS_PLATA:
            d[c] = _int(d[c]) or 0
        for c in ("vigencia", "periodo", "plazo_dias", "numero_cdp", "numero_crp",
                  "tipo_compromiso_cod", "modalidad_cod", "bp_sap",
                  "responsable_id", "solicitante_id",
                  "interno_crp", "posicion_crp", "interno_cdp", "posicion_cdp"):
            d[c] = _int(d[c])
        for c in ("fecha_registro", "fecha_entrada", "reporte_desde", "reporte_hasta",
                  "fecha_inicio_compromiso", "fecha_fin_compromiso"):
            d[c] = _fecha(d[c])
        d["num_doc"] = (str(d["num_doc"]).strip() if d["num_doc"] is not None else None)
        d["compromiso_raw"] = (str(d["compromiso_raw"]).strip()
                               if d["compromiso_raw"] is not None else None)
        filas.append(d)
    wb.close()
    return filas


def validar(filas, totales_esperados=None) -> dict:
    """Comprueba el archivo ANTES de escribir nada. Devuelve los totales.

    Tres controles, y ninguno sobra:

    1. **La PK natural sin duplicados.** Con un duplicado el upsert quedaría
       en el último que pase, y cargar dos veces daría cifras distintas.
    2. **La aritmética de cada fila.** `valor_neto` tiene que ser
       `valor_crp − anulaciones − reintegros`, y `sin_aut_giro` igual con el
       girado. Si no cuadra, la fila viene mal de la fuente.
    3. **Los seis totales.** Un reporte truncado a la mitad se ve bien fila
       por fila; solo el total lo delata.
    """
    if not filas:
        raise CargaError("El archivo no tiene filas de datos.")

    pk = [(f["interno_crp"], f["posicion_crp"]) for f in filas]
    if len(pk) != len(set(pk)):
        from collections import Counter
        dup = [k for k, n in Counter(pk).items() if n > 1][:5]
        raise CargaError(
            f"El archivo trae {len(pk) - len(set(pk))} filas con la misma "
            f"(N° Interno CRP, N° Posición CRP). Ejemplos: {dup}. Sin PK única "
            f"la carga no puede ser idempotente.")

    # EL REINTEGRO NO ENTRA EN EL NETO, y la especificación decía que sí.
    #
    #     valor_neto = valor_crp − anulaciones          ← lo que hace BogData
    #     valor_neto = valor_crp − anulaciones − reintegros  ← lo que decía
    #
    # Verificado en las 2.630 filas (0 fallos contra 2) y en el total del
    # propio archivo: 264.234.015.563 − 37.489.033.424 = 226.744.982.139, que
    # es exactamente el «Valor Neto» declarado. Restando además los
    # reintegros daría 226.732.640.339, que no aparece en ninguna parte.
    #
    # Tiene sentido contable: el reintegro es plata que VOLVIÓ después de
    # girarse, no una reducción del compromiso. Por eso las dos únicas filas
    # con reintegro son las que delataban la fórmula equivocada: un contrato
    # con $6.770.000 reintegrados conserva su neto de $74.470.000.
    malas = []
    for f in filas:
        neto = f["valor_crp"] - f["anulaciones"]
        sin_giro = f["valor_neto"] - f["autorizacion_giro"]
        if neto != f["valor_neto"] or sin_giro != f["sin_autorizacion_giro"]:
            malas.append((f["interno_crp"], f["posicion_crp"]))
    if malas:
        raise CargaError(
            f"{len(malas)} filas no cuadran su propia aritmética "
            f"(valor_neto ≠ crp − anulaciones, o sin_aut_giro ≠ neto − girado). "
            f"Ejemplos: {malas[:5]}.")

    totales = {c: sum(f[c] for f in filas) for c in CAMPOS_PLATA}

    if totales_esperados:
        difs = {c: (totales[c], totales_esperados[c])
                for c in totales_esperados if totales[c] != totales_esperados[c]}
        if difs:
            detalle = "; ".join(
                f"{c}: leído {a:,} contra {b:,} esperado" for c, (a, b) in difs.items())
            raise CargaError(
                f"Los totales de control no cuadran y la carga se aborta: {detalle}. "
                f"Un reporte incompleto se ve bien fila por fila.")

    return totales


def _tipo_doc_codigo(cur, tipo_doc: str):
    """El código numérico de `tipo_documento` para el texto del reporte.

    `crp.tipo_doc_bp_beneficiario_codigo` es un integer con FK al catálogo,
    pero el archivo trae texto («CC», «NIT»). Se resuelve por nombre y se
    devuelve `None` si el catálogo no lo tiene: inventar un código rompería la
    FK, y el texto queda igual guardado en `tercero_sap.tipo_doc`.
    """
    if not tipo_doc:
        return None
    cur.execute("SELECT codigo FROM tipo_documento WHERE UPPER(nombre) = %s "
                "OR UPPER(descripcion) = %s LIMIT 1",
                [tipo_doc.upper(), tipo_doc.upper()])
    fila = cur.fetchone()
    return fila[0] if fila else None


def _upsert_terceros(cur, filas) -> dict:
    """{(tipo_doc, num_doc): id}. Un solo viaje por tercero distinto."""
    from apps.presupuesto.models import TerceroSap

    vistos = {}
    for f in filas:
        td, nd = (f["tipo_doc"] or "").strip().upper(), f["num_doc"]
        if not td or not nd:
            continue
        # El ÚLTIMO nombre visto gana: el archivo trae variantes del mismo
        # tercero y no hay forma de saber cuál es la buena, pero al menos
        # todas las cargas convergen al mismo criterio.
        vistos[(td, nd)] = (f.get("tercero_nombre"), f.get("bp_sap"))

    salida = {}
    for (td, nd), (nombre, bp) in vistos.items():
        obj, _ = TerceroSap.objects.update_or_create(
            tipo_doc=td, num_doc=nd,
            defaults={"nombre": (str(nombre)[:200] if nombre else None),
                      "bp_sap": bp, "es_juridica": es_persona_juridica(td)},
        )
        salida[(td, nd)] = obj.id
    return salida


def _mapa_contratos(cur) -> dict:
    """{(numero, vigencia): contrato_id} de los contratos de innovaK."""
    cur.execute("SELECT id, contrato_numero, contrato_vigencia FROM contrato "
                "WHERE contrato_numero IS NOT NULL AND contrato_vigencia IS NOT NULL")
    return {(int(n), int(v)): cid for cid, n, v in cur.fetchall()}


def _mapa_proyectos(cur) -> dict:
    """{código sin ceros: proyecto_id}."""
    cur.execute("SELECT id, codigo FROM proyecto WHERE codigo IS NOT NULL")
    return {str(c).lstrip("0"): pid for pid, c in cur.fetchall() if str(c).strip()}


def _sembrar_catalogos(cur, filas) -> None:
    """Puebla rubro, tipo_compromiso, modalidad_seleccion y fondo desde el
    propio archivo. `ON CONFLICT DO NOTHING`: la segunda carga no los pisa."""
    rubros = {}
    for f in filas:
        r = (f["rubro"] or "").strip()
        if r:
            rubros[r] = (f.get("rubro_desc"), tipo_de_rubro(r), proyecto_de_rubro(r))
    for cod, (desc, tipo, proy) in rubros.items():
        cur.execute("""
            INSERT INTO rubro (codigo, descripcion, tipo, proyecto_cod)
            VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING
        """, [cod, desc, tipo, proy])

    for tabla, campo_cod, campo_nom in (
        ("tipo_compromiso", "tipo_compromiso_cod", "tipo_compromiso_desc"),
        ("modalidad_seleccion", "modalidad_cod", "modalidad_desc"),
    ):
        vals = {f[campo_cod]: f[campo_nom] for f in filas if f[campo_cod] is not None}
        for cod, nom in vals.items():
            cur.execute(
                f"INSERT INTO {tabla} (codigo, nombre) VALUES (%s, %s) "
                f"ON CONFLICT (codigo) DO NOTHING", [cod, nom])

    fondos = {(f["fondo_cod"] or "").strip(): f.get("fondo_desc")
              for f in filas if (f["fondo_cod"] or "").strip()}
    for cod, desc in fondos.items():
        cur.execute("INSERT INTO fondo (codigo, descripcion) VALUES (%s, %s) "
                    "ON CONFLICT (codigo) DO NOTHING", [cod, desc])

    # `periodo_fiscal` estaba vacía y `crp.periodo_codigo` tiene FK contra
    # ella. El «Período» del reporte es el MES (1-9 en este corte), así que la
    # llave se arma como AAAA-MM: un código «1» pelado se confundiría entre
    # vigencias, y el catálogo ya trae las columnas `anio` y `mes` para esto.
    periodos = {(f["vigencia"], f["periodo"]) for f in filas
                if f["vigencia"] and f["periodo"]}
    for anio, mes in sorted(periodos):
        cur.execute("""
            INSERT INTO periodo_fiscal (codigo, anio, mes, descripcion)
            VALUES (%s, %s, %s, %s) ON CONFLICT (codigo) DO NOTHING
        """, [f"{anio}-{mes:02d}", anio, mes, f"{MESES[mes]} de {anio}"])


@transaction.atomic
def cargar_crp(ruta, usuario=None, totales_esperados=None, nota=None) -> dict:
    """Carga el reporte entero. Todo o nada.

    Idempotente por `(interno_crp, posicion_crp)`: correrlo dos veces con el
    mismo archivo deja la base igual, no duplica.
    """
    from django.db import connection

    from apps.presupuesto.models import CrpCarga

    filas = leer(ruta)
    totales = validar(filas, totales_esperados)

    h = CrpCarga.hash_de(ruta)
    previa = CrpCarga.objects.filter(hash_sha256=h).first()
    if previa:
        raise CargaError(
            f"Este archivo ya se cargó: corte {previa.fecha_corte}, subido el "
            f"{previa.created_at:%Y-%m-%d}. Si es un corte nuevo, el archivo "
            f"tiene que ser distinto.")

    p = filas[0]
    carga = CrpCarga.objects.create(
        archivo_nombre=os.path.basename(ruta), hash_sha256=h,
        fecha_corte=p["reporte_hasta"], fecha_inicio_reporte=p["reporte_desde"],
        centro_gestor=None, vigencia=p["vigencia"],
        filas_leidas=len(filas), nota=nota,
        cargado_por_id=getattr(usuario, "id", None),
        **{f"total_{k}": Decimal(totales[c]) for k, c in (
            ("valor_crp", "valor_crp"), ("anulaciones", "anulaciones"),
            ("reintegros", "reintegros"), ("valor_neto", "valor_neto"),
            ("aut_giro", "autorizacion_giro"),
            ("sin_aut_giro", "sin_autorizacion_giro"))},
    )

    with connection.cursor() as cur:
        _sembrar_catalogos(cur, filas)
        terceros = _upsert_terceros(cur, filas)
        contratos = _mapa_contratos(cur)
        proyectos = _mapa_proyectos(cur)
        tipos_doc = {}

        sin_contrato, sin_proyecto, choques_pep = set(), set(), []
        insertadas = actualizadas = 0

        for f in filas:
            num, anio = normalizar_numero_compromiso(f["compromiso_raw"])
            contrato_id = contratos.get((num, anio)) if num and anio else None
            if num and anio and contrato_id is None:
                sin_contrato.add(f["compromiso_raw"])

            tipo_r = tipo_de_rubro(f["rubro"])
            cod_proy = proyecto_de_rubro(f["rubro"])
            cod_pep = proyecto_de_pep(f["elemento_pep"])
            # Las dos vías tienen que coincidir. Cuando no, se REPORTA y no se
            # elige una: la discrepancia significa que la fuente trae mal
            # escrito el rubro o el PEP, y taparla dejaría el CRP colgado del
            # proyecto equivocado sin que nadie se entere.
            if cod_proy and cod_pep and cod_proy != cod_pep:
                choques_pep.append((f["interno_crp"], f["rubro"], f["elemento_pep"]))
            proyecto_id = proyectos.get(cod_proy) if cod_proy else None
            if tipo_r == "inversion" and proyecto_id is None:
                sin_proyecto.add(f["rubro"])

            td = (f["tipo_doc"] or "").strip().upper()
            if td and td not in tipos_doc:
                tipos_doc[td] = _tipo_doc_codigo(cur, td)

            cur.execute("""
                INSERT INTO crp (
                    n_interno_crp, n_posicion_crp, n_interno_cdp, n_posicion_cdp,
                    carga_id, tercero_id, contrato_id, proyecto_id,
                    ejercicio, periodo_codigo, fecha_registro,
                    tipo_compromiso_codigo, tipo_compromiso_desc,
                    no_compromiso, compromiso_numero, compromiso_anio,
                    fecha_inicio_compromiso, fecha_fin_compromiso, plazo_dias,
                    numero_de_cdp, numero_de_crp, objeto,
                    rubro_codigo, rubro_desc, fondo_codigo, fondo_desc,
                    concepto_gasto_codigo, descripcion_concepto_gasto,
                    elemento_pep, texto_id_proyecto,
                    modalidad_seleccion_codigo, modalidad_desc,
                    bp_beneficiario, tipo_doc_bp_beneficiario_codigo,
                    numero_doc_bp_beneficiario, nombre_bp_beneficiario,
                    id_responsable, responsable, id_solicitante, nombre_solicitante,
                    valor_crp, anulaciones, reintegros, valor_neto,
                    autorizacion_giro, com_sin_aut_giro,
                    fecha_de_entrada, programa_financiamiento,
                    es_obligacion_por_pagar, es_funcionamiento, vigente, updated_at
                ) VALUES (
                    %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s, %s,%s,%s,
                    %s,%s,%s, %s,%s,%s, %s,%s,%s,%s, %s,%s, %s,%s, %s,%s,
                    %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,
                    %s,%s,TRUE, now()
                )
                ON CONFLICT (n_interno_crp, n_posicion_crp) DO UPDATE SET
                    carga_id = EXCLUDED.carga_id,
                    tercero_id = EXCLUDED.tercero_id,
                    contrato_id = EXCLUDED.contrato_id,
                    proyecto_id = EXCLUDED.proyecto_id,
                    valor_crp = EXCLUDED.valor_crp,
                    anulaciones = EXCLUDED.anulaciones,
                    reintegros = EXCLUDED.reintegros,
                    valor_neto = EXCLUDED.valor_neto,
                    autorizacion_giro = EXCLUDED.autorizacion_giro,
                    com_sin_aut_giro = EXCLUDED.com_sin_aut_giro,
                    objeto = EXCLUDED.objeto,
                    vigente = TRUE,
                    updated_at = now()
                RETURNING (xmax = 0) AS insertada
            """, [
                f["interno_crp"], f["posicion_crp"], f["interno_cdp"], f["posicion_cdp"],
                carga.id, terceros.get((td, f["num_doc"])), contrato_id, proyecto_id,
                f["vigencia"],
                (f"{f['vigencia']}-{f['periodo']:02d}"
                 if f["vigencia"] and f["periodo"] else None),
                f["fecha_registro"],
                f["tipo_compromiso_cod"], f["tipo_compromiso_desc"],
                f["compromiso_raw"], num, anio,
                f["fecha_inicio_compromiso"], f["fecha_fin_compromiso"], f["plazo_dias"],
                f["numero_cdp"], f["numero_crp"], f["objeto"],
                f["rubro"], f["rubro_desc"], f["fondo_cod"], f["fondo_desc"],
                f["concepto_gasto_cod"], f["concepto_gasto_desc"],
                f["elemento_pep"], f["texto_id_proyecto"],
                f["modalidad_cod"], f["modalidad_desc"],
                f["bp_sap"], tipos_doc.get(td), f["num_doc"], f["tercero_nombre"],
                f["responsable_id"], f["responsable_nombre"],
                f["solicitante_id"], f["solicitante_nombre"],
                f["valor_crp"], f["anulaciones"], f["reintegros"], f["valor_neto"],
                f["autorizacion_giro"], f["sin_autorizacion_giro"],
                f["fecha_entrada"], f["programa_financiamiento"],
                tipo_r == "obligacion_por_pagar", tipo_r == "funcionamiento",
            ])
            if cur.fetchone()[0]:
                insertadas += 1
            else:
                actualizadas += 1

        # Lo que ya no viene se marca, no se borra.
        cur.execute("""
            UPDATE crp SET vigente = FALSE, updated_at = now()
            WHERE vigente AND carga_id IS DISTINCT FROM %s AND carga_id IS NOT NULL
        """, [carga.id])
        no_vigentes = cur.rowcount

    carga.filas_insertadas = insertadas
    carga.filas_actualizadas = actualizadas
    carga.filas_no_vigentes = no_vigentes
    carga.compromisos_sin_contrato = len(sin_contrato)
    carga.rubros_sin_proyecto = len(sin_proyecto)
    carga.save(update_fields=["filas_insertadas", "filas_actualizadas",
                              "filas_no_vigentes", "compromisos_sin_contrato",
                              "rubros_sin_proyecto"])

    return {
        "carga_id": carga.id, "fecha_corte": carga.fecha_corte,
        "leidas": len(filas), "insertadas": insertadas,
        "actualizadas": actualizadas, "no_vigentes": no_vigentes,
        "totales": totales,
        "compromisos_sin_contrato": sorted(sin_contrato),
        "rubros_sin_proyecto": sorted(sin_proyecto),
        "choques_rubro_pep": choques_pep,
    }
