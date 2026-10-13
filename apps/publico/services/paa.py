"""El Plan Anual de Adquisiciones de Kennedy, para consumo público.

Es lo que el plan dice que se va a contratar. Sirve para una pregunta concreta
que hoy nadie puede responder desde afuera: ¿este contrato estaba planeado, y
con cuánta plata?

## Los cuatro recortes, declarados antes de que alguien los descubra solo

1. **No hay historial de versiones.** El PAA 2025 de Kennedy va en la versión
   31 y la fuente publica SOLO esa: una versión distinta por año en los dos
   datasets. Qué cambió entre la 30 y la 31 no está publicado en ninguna parte.
   Se da el número y su fecha; no se puede reconstruir nada.

2. **Los procesos solo existen desde 2024.** De 2017 a 2023 no hay ni un
   proceso declarado en las 3.292 filas de esos años. O sea: para esos años el
   PAA no se puede cruzar con contratos, y no por falta nuestra.

3. **El SIPSE solo cubre 2025 y 2026** (354 y 547 procesos). Antes, cero.

4. **El código interno cambia de convención cada año**, así que no es una serie
   comparable: K-0528 en 2025-2026, ID_900 en 2024, y en 2022 un compuesto
   —PS-345-2178-2767-14919— que trae el proyecto y la meta adentro. Por eso
   viaja `codigo_interno_tipo`: sin él, comparar 2024 con 2025 parece legítimo.

## Y el recorte del cruce, que son DOS cifras y no una

    de los 1.806 avisos del PAA, están en nuestro espejo .. 96,4 %
    de nuestros 3.211 contratos, están en el PAA .......... 70,5 %
      2024 .... 30,3 %   ·   2025 .... 99,7 %   ·   2026 .... 83,5 %

La segunda es la que importa para decir «el plan detrás de este contrato», y es
la baja. Confundir las dos direcciones es el error que ya produjo una cobertura
del 160 % en este proyecto.
"""
from django.db import connection

#: Lo que se puede filtrar, y su SQL. Igual que en contratos: un parámetro que
#: no está acá se RECHAZA, no se ignora — `?anoo=2025` devolviendo el dataset
#: entero con un 200 es indistinguible de «ese año tiene todo».
FILTROS = {
    "anio": "i.anio = %s",
    "codigo_interno": "i.codigo_interno = %s",
    "modalidad": "i.modalidad = %s",
    "actualizado_desde": "i.synced_at >= %s",
    # El SIPSE vive en la tabla de procesos: se filtra por existencia para no
    # multiplicar el ítem por sus procesos.
    "codigo_sipse": ("EXISTS (SELECT 1 FROM paa_item_proceso p "
                     "WHERE p.item_id = i.item_id AND p.proceso_sipse = %s)"),
    "referencia_proceso": ("EXISTS (SELECT 1 FROM paa_item_proceso p "
                           "WHERE p.item_id = i.item_id AND p.proceso_ref = %s)"),
}

PARAMETROS_VALIDOS = set(FILTROS) | {"q", "cursor", "limite", "con_proceso"}

MOTIVO_SIN_HISTORIAL = (
    "La fuente publica solo la ÚLTIMA versión del PAA de cada año. Este número "
    "dice en qué versión va; lo que cambió entre una y otra no está publicado."
)

MOTIVO_SIN_PROCESO_ANTES_2024 = (
    "De 2017 a 2023 el PAA de Kennedy no declara ni un proceso: 3.292 filas, "
    "cero procesos. Para esos años el plan no se puede cruzar con contratos."
)

MOTIVO_SIPSE_DESDE_2025 = (
    "El código de SIPSE aparece en el PAA desde 2025 (354 procesos) y 2026 "
    "(547). Antes no lo trae ninguna fila."
)

MOTIVO_CODIGO_NO_COMPARABLE = (
    "El código interno cambia de convención cada año y NO es una serie "
    "comparable: K-#### en 2025-2026, ID_### en 2024, y en 2022 un compuesto "
    "que trae proyecto y meta adentro. `codigo_interno_tipo` dice cuál es."
)

_CAMPOS = """
    i.item_id, i.anio, i.identificador_unico, i.descripcion,
    i.codigo_interno, i.codigo_interno_tipo,
    i.valor_total_esperado, i.valor_presupuesto,
    i.fecha_esperada_inicio, i.fecha_esperada_recepcion,
    i.duracion_esperada, i.unidad_duracion,
    i.modalidad, i.origen_recursos, i.categorias_unspsc,
    i.estado_solicitud, i.tipo, i.causal_contratacion, i.grupo_procedimiento,
    i.requiere_vigencias_fut, i.version_paa, i.fecha_version, i.synced_at
"""

_ORDEN = "ORDER BY i.item_id"


class ParametroDesconocido(ValueError):
    def __init__(self, desconocidos):
        self.desconocidos = sorted(desconocidos)
        super().__init__(
            "Parámetros que esta API no reconoce: " + ", ".join(self.desconocidos)
            + ". Válidos: " + ", ".join(sorted(PARAMETROS_VALIDOS)) + ".")


def validar_parametros(recibidos) -> None:
    desconocidos = [p for p in recibidos if p not in PARAMETROS_VALIDOS]
    if desconocidos:
        raise ParametroDesconocido(desconocidos)


def _unspsc(v):
    """Los UNSPSC vienen como lista separada por `;` y a veces uno solo.

    Se devuelven como lista para no obligar a nadie a partir una cadena, y se
    deja el crudo al lado porque el separador del origen podría cambiar.
    """
    if not v:
        return [], None
    partes = [p.strip() for p in str(v).replace(",", ";").split(";")]
    return [p for p in partes if p], str(v)


def _fila(r, procesos):
    (item_id, anio, cab, desc, cod, cod_tipo, valor, presu, f_ini, f_rec,
     dur, uni, modalidad, origen, unspsc, estado, tipo, causal, grupo,
     vig_fut, version, f_version, synced) = r
    codigos, crudo = _unspsc(unspsc)
    return {
        "item_id": item_id,
        "anio": anio,
        "paa": {
            "identificador": cab,
            "version": version,
            "fecha_version": f_version.isoformat() if f_version else None,
            "version_motivo": MOTIVO_SIN_HISTORIAL,
        },
        "descripcion": desc,
        "codigo_interno": cod,
        "codigo_interno_tipo": cod_tipo,
        "codigo_interno_motivo": (MOTIVO_CODIGO_NO_COMPARABLE if cod
                                  else "El PAA de este año no usa código interno."),
        "valor": {
            "total_esperado_cop": float(valor) if valor is not None else None,
            "presupuesto_cop": float(presu) if presu is not None else None,
        },
        "duracion": {"esperada": dur, "unidad": uni},
        "fechas_esperadas": {"inicio": f_ini, "recepcion": f_rec},
        "modalidad": modalidad,
        "origen_recursos": origen,
        "unspsc": codigos,
        "unspsc_origen": crudo,
        "estado_solicitud": estado,
        "tipo": tipo,
        "causal_contratacion": causal,
        "grupo_procedimiento": grupo,
        "requiere_vigencias_futuras": vig_fut,
        # La lista, no un campo único: un ítem planeado puede ir a varios
        # procesos (216 casos) y quedarse con uno borraría los otros.
        "procesos": procesos.get(item_id, []),
        "actualizado": synced.isoformat() if synced else None,
    }


def _procesos(cur, ids):
    if not ids:
        return {}
    cur.execute("""
        SELECT item_id, proceso_estado, proceso_ref, proceso_sipse,
               proceso_notice_id, url_proceso, proceso_ref_origen
        FROM paa_item_proceso
        WHERE item_id = ANY(%s)
        ORDER BY item_id, proceso_ref_origen
    """, [list(ids)])
    salida: dict[str, list] = {}
    for iid, estado, ref, sipse, aviso, url, crudo in cur.fetchall():
        salida.setdefault(iid, []).append({
            "estado": estado,
            "referencia": ref,
            "codigo_sipse": sipse,
            "codigo_sipse_motivo": (None if sipse else MOTIVO_SIPSE_DESDE_2025),
            # La llave para cruzar con /contratos/: es el mismo identificador
            # que `contrato.proceso.aviso`.
            "aviso": aviso,
            "url": url,
            # El texto tal como lo trae el plan. Es lo único que se puede leer
            # cuando el estado es `ilegible`.
            "origen": crudo,
        })
    return salida


def _where(filtros, cursor_id):
    partes, params = [], []
    for clave, sql in FILTROS.items():
        valor = filtros.get(clave)
        if valor not in (None, ""):
            partes.append(sql)
            params.append(valor)
    if filtros.get("q"):
        partes.append("(i.descripcion ILIKE %s OR i.codigo_interno ILIKE %s)")
        params += [f"%{filtros['q']}%"] * 2
    if filtros.get("con_proceso") in ("1", "true", "True", True):
        partes.append("EXISTS (SELECT 1 FROM paa_item_proceso p "
                      "WHERE p.item_id = i.item_id "
                      "AND p.proceso_estado = 'declarado')")
    if cursor_id:
        partes.append("i.item_id > %s")
        params.append(cursor_id)
    return ("WHERE " + " AND ".join(partes)) if partes else "", params


def listar(filtros: dict | None = None, cursor_id=None, limite=50) -> dict:
    """Una página del PAA. Cursor sobre `item_id`, como en contratos."""
    filtros = filtros or {}
    limite = max(1, min(int(limite or 50), 500))
    where, params = _where(filtros, cursor_id)
    with connection.cursor() as cur:
        cur.execute(f"SELECT {_CAMPOS} FROM paa_item i {where} {_ORDEN} "
                    f"LIMIT %s", params + [limite + 1])
        filas = cur.fetchall()
        hay_mas = len(filas) > limite
        filas = filas[:limite]
        procesos = _procesos(cur, [f[0] for f in filas])
        where_total, params_total = _where(filtros, None)
        cur.execute(f"SELECT COUNT(*) FROM paa_item i {where_total}", params_total)
        total = int(cur.fetchone()[0] or 0)
    return {
        "count": total,
        "next_cursor": (filas[-1][0] if hay_mas and filas else None),
        "results": [_fila(f, procesos) for f in filas],
        "recortes": {
            "sin_historial_de_versiones": MOTIVO_SIN_HISTORIAL,
            "sin_procesos_antes_de_2024": MOTIVO_SIN_PROCESO_ANTES_2024,
            "sipse_desde_2025": MOTIVO_SIPSE_DESDE_2025,
            "codigo_interno_no_comparable": MOTIVO_CODIGO_NO_COMPARABLE,
        },
    }


def detalle(item_id: str) -> dict | None:
    if not item_id or "/" in item_id:
        return None
    with connection.cursor() as cur:
        cur.execute(f"SELECT {_CAMPOS} FROM paa_item i WHERE i.item_id = %s",
                    [item_id])
        fila = cur.fetchone()
        if not fila:
            return None
        procesos = _procesos(cur, [fila[0]])
    return _fila(fila, procesos)


def cobertura() -> dict:
    """Las cifras del PAA, medidas en vivo, por año.

    Va al lado del dato y no en un correo: un consumidor que arma un informe
    con esto tiene que poder ver que 2017-2023 no tiene procesos sin que nadie
    se lo cuente.
    """
    with connection.cursor() as cur:
        cur.execute("""
            SELECT i.anio,
                   COUNT(DISTINCT i.item_id),
                   COUNT(DISTINCT i.item_id)
                       FILTER (WHERE i.codigo_interno IS NOT NULL),
                   COUNT(p.id) FILTER (WHERE p.proceso_estado = 'declarado'),
                   COUNT(p.id) FILTER (WHERE p.proceso_sipse IS NOT NULL),
                   MAX(i.version_paa)
            FROM paa_item i
            LEFT JOIN paa_item_proceso p ON p.item_id = i.item_id
            GROUP BY 1 ORDER BY 1
        """)
        por_anio = [
            {"anio": a, "items": it, "con_codigo_interno": cod,
             "procesos_declarados": decl, "con_codigo_sipse": sip,
             "version_del_paa": ver}
            for a, it, cod, decl, sip, ver in cur.fetchall()
        ]
        cur.execute("""
            SELECT COUNT(DISTINCT p.proceso_notice_id),
                   COUNT(DISTINCT p.proceso_notice_id)
                       FILTER (WHERE s.id_contrato IS NOT NULL)
            FROM paa_item_proceso p
            LEFT JOIN secop_contrato s
                   ON s.proceso_notice_id = p.proceso_notice_id
            WHERE p.proceso_notice_id IS NOT NULL
        """)
        avisos, avisos_ok = cur.fetchone()
        cur.execute("""
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM paa_item_proceso p
                        WHERE p.proceso_notice_id = s.proceso_notice_id))
            FROM secop_contrato s
        """)
        contratos, contratos_ok = cur.fetchone()
    return {
        "por_anio": por_anio,
        # Las DOS direcciones, nombradas, porque son dos cifras distintas.
        "cruce_con_contratos": {
            "avisos_del_paa_en_nuestro_espejo": {
                "n": avisos_ok, "de": avisos,
                "pct": round(100.0 * avisos_ok / avisos, 1) if avisos else None},
            "nuestros_contratos_en_el_paa": {
                "n": contratos_ok, "de": contratos,
                "pct": round(100.0 * contratos_ok / contratos, 1)
                       if contratos else None},
            "nota": ("Son dos cifras distintas. La segunda es la que importa "
                     "para decir «el plan detrás de este contrato», y es la "
                     "baja. Confundirlas ya produjo una cobertura del 160 % "
                     "en este proyecto."),
        },
        "recortes": {
            "sin_historial_de_versiones": MOTIVO_SIN_HISTORIAL,
            "sin_procesos_antes_de_2024": MOTIVO_SIN_PROCESO_ANTES_2024,
            "sipse_desde_2025": MOTIVO_SIPSE_DESDE_2025,
            "codigo_interno_no_comparable": MOTIVO_CODIGO_NO_COMPARABLE,
        },
        "fuente": "datos.gov.co — 9sue-ezhx (ítems) y b6m4-qgqv (encabezado)",
    }
