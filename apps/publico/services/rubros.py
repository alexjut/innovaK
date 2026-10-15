"""El rubro presupuestal de cada contrato, desde el CRP de BogData.

SECOP no publica el rubro. El CRP sí, y además trae el CDP, el CRP y —dentro
del código del rubro de inversión— el proyecto del Plan de Desarrollo. Pero el
CRP no trae el identificador del contrato de SECOP: hay que enlazarlo.

## El enlace, y por qué exige el documento del contratista

El CRP numera su compromiso como «376-2026», que es el número y la vigencia del
contrato. Eso se cruza con `referencia_contrato` partida por el regex de la
casa. Medido el 2026-10-15: 2.592 de 2.670 filas parseables enlazan (97,1 %) y
2.251 contratos recibirían rubro.

Pero ese enlace, solo, ATRIBUYE PLATA AL CONTRATO EQUIVOCADO en 53 pares / 42
contratos / $4.317 millones, de los cuales $2.918 M son de inversión y quedan
colgados de tres proyectos del PDL que no son. La causa: **el Fondo numera los
convenios, las resoluciones y los CPS en el MISMO espacio numérico**, y el
regex tira el prefijo. El caso que lo muestra:

    CRP, compromiso «628-2026»:
      CPS      Karoll Cárdenas         $48,0 M    proyecto 2711
      CONVENIO IDARTES              $1.167,1 M    proyecto 2780
      CONVENIO IDARTES                $845,7 M    proyecto 2788
      CONVENIO SCRD                   $449,3 M    proyecto 2788
      CONVENIO SCRD                   $406,4 M    proyecto 2780
    SECOP, CPS-628-2026: Karoll Cárdenas, $48,0 M

El convenio 628-2026 es otro instrumento, con otro CDP y otro CRP, y no está en
el espejo. Sin corroborar, sus $2.868 M se le cuelgan al contrato de $48 M de
una persona.

Eso NO se ve contando colisiones: una colisión exige dos contratos compitiendo
por la misma llave, y acá el espejo tiene uno solo. Medido por colisiones el
riesgo parecía de 7 filas (0,27 %); el daño real es veinte veces mayor.

Lo que sí lo caza es **el documento de la contraparte**: los 53 pares falsos
tienen todos un documento distinto, así que exigir que coincida los elimina al
100 %. Cuesta cobertura —de 2.251 contratos a 2.071— y es el precio correcto:
un rubro equivocado le atribuye gasto público a un proyecto que no es.

## Lo que NO se publica, y por qué

**El rubro de un par no corroborado.** Quedan 187 pares donde el número, el
objeto palabra por palabra y el valor al céntimo coinciden, pero el contratista
es otra persona. Hay dos explicaciones posibles —una cesión, o la columna
`proveedor` del espejo desalineada— y el dato no permite decidir cuál. Se
declara la discrepancia y no se publica el rubro.

**El beneficiario del CRP como contratista del contrato.** En esos 187 pares
las dos fuentes nombran personas distintas y no se sabe cuál tiene razón.

**Un cero donde no hay dato.** Los 1.529 contratos de 2020-2022 quedan fuera
del corte del CRP (2026-10-05): su rubro es DESCONOCIDO, no vacío ni cero.

## Por qué es una LISTA y no un campo

12 contratos reciben más de un rubro, y es legítimo: el par de obligaciones por
pagar O230689 + O230690 es el mismo dinero partido por antigüedad del saldo, y
un contrato de seguros reparte entre cinco rubros CPC.

Y el hallazgo que más condiciona el uso: **1.382 contratos (61,4 %, $120.992 M)
solo reciben rubro de Obligaciones por Pagar**, que no nombra proyecto. Quien
quiera saber a qué proyecto se imputó el gasto lo tendrá en 797 contratos, no
en 2.071.
"""
import re

from django.db import connection

#: Lo que el CRP llama compromiso pero NO es un contrato. Se excluye de entrada:
#: son resoluciones de pago de parafiscales, actas y facturas que llevan número
#: y chocan contra los CPS. Las 14 resoluciones de COMPENSAR enlazaban a CPS al
#: azar, con beneficiario «CAJA DE COMPENSACION FAMILIAR COMPENSAR».
TIPOS_NO_CONTRATO = (
    "RESOLUCION", "ACTAS", "FACTURAS", "RELACION DE AUTORIZACION",
    "ORDEN DE COMPRA",
)

#: El regex de la casa con tres tolerancias, medidas y no supuestas.
#:
#: El de `kpis_presupuesto._REF_SECOP_RX` parsea 5.377 de 5.558 referencias
#: (96,7 %). Los 181 que deja fuera no son basura: 110 vienen con el código de
#: la entidad delante —`FDLK-CPS-123-2026`—, 12 más con otras familias igual
#: prefijadas, y 13 traen el separador sucio (`CPS.127.2021`, `CPS--287-2021`,
#: `CPS/366/2022`). Admitiendo el `FDLK-` opcional y cualquiera de `-./`
#: repetidos se llega a 5.539 (99,7 %), y se comprobó que de las 5.377 que YA
#: parseaban NINGUNA cambia de resultado: es una mejora estricta.
#:
#: Quedan 19 fuera y no se fuerzan: 6 sin prefijo (`054-2024`), 3 que traen el
#: identificador de SECOP en el campo de la referencia, y 2 en prosa
#: («CIA No. 534 DE 2021»).
#:
#: No se toca el regex compartido: de él dependen las conciliaciones por
#: (número, vigencia) del muro de subgrupos y del expediente de proyecto, y
#: cambiarlo movería cifras ya publicadas. Queda anotado como hallazgo.
_REF = re.compile(r"^(?:FDLK\s*[-./]\s*)?([A-Z]+)\s*[-./]+\s*0*(\d+)"
                  r"\s*[-./]+\s*(\d{4})")

MOTIVO_SIN_CRP = (
    "No hay CRP cargado para la vigencia de este contrato. El rubro es "
    "DESCONOCIDO, no inexistente: el reporte de BogData cargado tiene corte "
    "2026-10-05 y cubre la vigencia 2026 más las obligaciones por pagar de "
    "años anteriores, así que los contratos de 2020-2022 quedan fuera."
)

MOTIVO_SIN_ENLACE = (
    "El CRP no tiene un compromiso con el número y la vigencia de este "
    "contrato. Lo más común no es un defecto del enlace: el reporte cargado "
    "cubre UNA vigencia más las obligaciones por pagar de años anteriores, así "
    "que un contrato pagado por completo dentro de su propia vigencia no "
    "aparece en el CRP de la siguiente. Para que aparezca hay que cargar el "
    "reporte de SU vigencia."
)

MOTIVO_NO_CORROBORADO = (
    "Se encontró un compromiso con ese número y vigencia, pero el documento de "
    "la contraparte NO coincide con el contratista de SECOP, así que no se "
    "publica el rubro. El Fondo numera convenios, resoluciones y contratos de "
    "prestación de servicios en el mismo espacio numérico: sin esa "
    "corroboración, 53 pares medidos atribuían $4.317 millones al contrato "
    "equivocado, $2.918 M de ellos a proyectos del Plan que no eran."
)

MOTIVO_REFERENCIA_ILEGIBLE = (
    "La referencia de este contrato no se puede partir en número y vigencia, "
    "que es la única llave que conecta con el CRP."
)

NOTA_OBLIGACION_POR_PAGAR = (
    "Un rubro de Obligaciones por Pagar no nombra proyecto: es deuda de una "
    "vigencia anterior pagada con la actual. 1.382 contratos (61,4 %) solo "
    "tienen rubros de esta clase."
)

_SQL = """
    SELECT compromiso_numero, compromiso_anio, rubro_codigo, rubro_desc,
           fondo_codigo, fondo_desc, numero_de_cdp, numero_de_crp,
           valor_crp, anulaciones, reintegros, valor_neto, autorizacion_giro,
           es_obligacion_por_pagar, es_funcionamiento,
           regexp_replace(coalesce(numero_doc_bp_beneficiario, ''),
                          '[^0-9]', '', 'g') AS doc,
           tipo_compromiso_desc, texto_id_proyecto
    FROM crp
    WHERE vigente
      AND compromiso_numero IS NOT NULL
      AND compromiso_anio IS NOT NULL
      AND tipo_compromiso_desc NOT IN %s
      AND (compromiso_numero, compromiso_anio) IN %s
"""


def _clase(es_oxp: bool, es_func: bool) -> str:
    """De dónde sale la plata. Se usa la BANDERA del CRP, no el prefijo.

    Las banderas ya están en la tabla y cuadran con los totales (1.690
    obligaciones por pagar, 68 funcionamiento). Re-derivarlas del código sería
    una segunda implementación de lo mismo, que es como nacen dos verdades.
    """
    if es_oxp:
        return "obligacion_por_pagar"
    if es_func:
        return "funcionamiento"
    return "inversion"


def _proyecto(rubro: str | None, clase: str) -> str | None:
    """El código del proyecto, que vive DENTRO del rubro de inversión.

    Solo para inversión y solo sobre los rubros `O2301…`: ahí las posiciones 16
    a 19 son el proyecto y dan cuatro dígitos en 1.058 de 1.058 filas medidas.
    Aplicada a un rubro de funcionamiento la misma fórmula devuelve basura con
    pinta de código válido —`O21202020080282130` da «130»—, así que va
    condicionada a la clase.
    """
    if clase != "inversion" or not rubro or not rubro.startswith("O2301"):
        return None
    trozo = rubro[15:19]
    return trozo if trozo.isdigit() else None


def _norm_proyecto(codigo: str | None) -> str | None:
    """Sin ceros a la izquierda. `proyecto.codigo` los guarda de dos formas.

    En la tabla hay `0002377` y `000007895` junto a `2491` y `2492`: comparar
    sin normalizar deja fuera a los dos primeros.
    """
    if not codigo:
        return None
    return codigo.lstrip("0") or codigo


def por_contrato(ids: list[str]) -> dict[str, dict]:
    """Los rubros de esos contratos. Siempre una entrada por cada id pedido."""
    if not ids:
        return {}
    ids = list(dict.fromkeys(ids))
    with connection.cursor() as cur:
        cur.execute("""SELECT id_contrato, referencia_contrato, anio,
                              regexp_replace(coalesce(documento_proveedor,''),
                                             '[^0-9]', '', 'g')
                       FROM secop_contrato WHERE id_contrato = ANY(%s)""", [ids])
        contratos = {r[0]: {"ref": r[1], "anio": r[2], "doc": r[3]}
                     for r in cur.fetchall()}

        llaves: dict[tuple, list] = {}
        for id_ct, c in contratos.items():
            m = _REF.match((c["ref"] or "").strip().upper())
            c["llave"] = (int(m.group(2)), int(m.group(3))) if m else None
            c["prefijo"] = m.group(1) if m else None
            if c["llave"]:
                llaves.setdefault(c["llave"], []).append(id_ct)

        filas: dict[tuple, list] = {}
        if llaves:
            cur.execute(_SQL, [TIPOS_NO_CONTRATO, tuple(llaves)])
            for f in cur.fetchall():
                filas.setdefault((f[0], f[1]), []).append(f)

        # Los proyectos del Plan, para poder decir si el código que trae el
        # rubro corresponde a uno real y no a un número que parece uno.
        cur.execute("SELECT codigo FROM proyecto")
        proyectos = {_norm_proyecto(r[0]) for r in cur.fetchall()}

    salida: dict[str, dict] = {}
    for id_ct in ids:
        c = contratos.get(id_ct)
        if c is None:
            salida[id_ct] = _vacio("sin_enlace", MOTIVO_SIN_ENLACE)
            continue
        if not c["llave"]:
            salida[id_ct] = _vacio("referencia_ilegible",
                                   MOTIVO_REFERENCIA_ILEGIBLE)
            continue
        candidatas = filas.get(c["llave"], [])
        if not candidatas:
            # Sin candidatas hay dos situaciones distintas y no se pueden
            # mezclar: que la vigencia esté fuera del corte del CRP, o que esté
            # dentro y el compromiso simplemente no exista.
            clave = ("sin_crp_para_la_vigencia" if (c["anio"] or 0) < 2023
                     else "sin_enlace")
            motivo = (MOTIVO_SIN_CRP if clave == "sin_crp_para_la_vigencia"
                      else MOTIVO_SIN_ENLACE)
            salida[id_ct] = _vacio(clave, motivo)
            continue

        corroboradas = [f for f in candidatas if f[15] and f[15] == c["doc"]]
        if not corroboradas:
            salida[id_ct] = _vacio(
                "no_corroborado", MOTIVO_NO_CORROBORADO,
                {"compromisos_encontrados": len(candidatas),
                 # Se dice CUÁNTOS hay y de qué tipo, sin publicar quién es:
                 # en estos pares las dos fuentes nombran personas distintas y
                 # no se sabe cuál tiene razón.
                 "tipos_encontrados": sorted({(f[16] or "") for f in candidatas})})
            continue

        salida[id_ct] = _armar(corroboradas, proyectos)
    return salida


def _vacio(codigo, motivo, extra=None):
    salida = {"rubros": [], "rubros_motivo": motivo, "motivo_codigo": codigo,
              "proyecto_codigo": None, "corroboracion": None}
    if extra:
        salida.update(extra)
    return salida


def _armar(filas, proyectos) -> dict:
    rubros = []
    for f in filas:
        clase = _clase(bool(f[13]), bool(f[14]))
        proy = _proyecto(f[2], clase)
        rubros.append({
            "codigo": f[2],
            "descripcion": f[3],
            "clase": clase,
            "fondo": {"codigo": f[4], "descripcion": f[5]},
            "cdp": f[6],
            "crp": f[7],
            "valor_crp_cop": float(f[8]) if f[8] is not None else None,
            "anulaciones_cop": float(f[9]) if f[9] is not None else None,
            "reintegros_cop": float(f[10]) if f[10] is not None else None,
            "valor_neto_cop": float(f[11]) if f[11] is not None else None,
            "autorizacion_giro_cop": float(f[12]) if f[12] is not None else None,
            "proyecto_codigo": proy,
            # Si el código que sale del rubro no está en el catálogo de
            # proyectos, se dice: un código con la forma correcta que no
            # corresponde a nada es peor que un null.
            "proyecto_en_catalogo": (None if proy is None
                                     else _norm_proyecto(proy) in proyectos),
            "nota": (NOTA_OBLIGACION_POR_PAGAR
                     if clase == "obligacion_por_pagar" else None),
        })
    rubros.sort(key=lambda r: (-(r["valor_neto_cop"] or 0), r["codigo"] or ""))

    # El proyecto a nivel de contrato SOLO cuando hay exactamente uno de
    # inversión. Con dos, publicar «el» proyecto elegiría uno por nosotros.
    de_inversion = {r["proyecto_codigo"] for r in rubros
                    if r["clase"] == "inversion" and r["proyecto_codigo"]}
    proyecto = de_inversion.pop() if len(de_inversion) == 1 else None

    # Una entrada por FILA del CRP, porque cada una trae su CDP, su CRP y su
    # valor: eso es el rastro auditable. Pero «pagado por tres CRP» y «tiene
    # tres rubros distintos» son hechos distintos, y el segundo es el
    # noticiable, así que se cuenta aparte.
    distintos = sorted({r["codigo"] for r in rubros if r["codigo"]})

    return {
        "rubros": rubros,
        "rubros_distintos": len(distintos),
        "codigos": distintos,
        "rubros_motivo": None,
        "motivo_codigo": None,
        "proyecto_codigo": proyecto,
        "proyecto_motivo": (None if proyecto else
                            ("Más de un proyecto de inversión en los rubros de "
                             "este contrato." if len(de_inversion) > 1 else
                             "Ningún rubro de inversión: no hay proyecto que "
                             "nombrar.")),
        # Cómo se comprobó el enlace. Viaja porque es la diferencia entre un
        # dato auditable y una coincidencia de números.
        "corroboracion": "documento_del_contratista",
    }


def cobertura() -> dict:
    """Cuántos contratos tienen rubro, y qué se pierde en cada paso."""
    with connection.cursor() as cur:
        cur.execute("SELECT DISTINCT id_contrato FROM secop_contrato")
        ids = [r[0] for r in cur.fetchall()]
        cur.execute("""SELECT MIN(fecha_inicio_reporte), MAX(fecha_corte),
                              COUNT(*) FROM crp_carga""")
        desde, corte, cargas = cur.fetchone()
    res = por_contrato(ids)
    from collections import Counter
    por_codigo = Counter(v["motivo_codigo"] or "con_rubro" for v in res.values())
    con = [v for v in res.values() if v["rubros"]]
    con_proy = [v for v in con if v["proyecto_codigo"]]
    solo_oxp = [v for v in con
                if all(r["clase"] == "obligacion_por_pagar" for r in v["rubros"])]
    return {
        "contratos": len(res),
        "con_rubro": len(con),
        "con_proyecto_del_plan": len(con_proy),
        "solo_obligaciones_por_pagar": len(solo_oxp),
        # Las dos cifras, porque son dos hechos: pagado por varios CRP (normal)
        # y tener varios rubros distintos (lo noticiable).
        "con_varias_filas_de_crp": sum(1 for v in con if len(v["rubros"]) > 1),
        "con_varios_rubros_distintos": sum(1 for v in con
                                           if v.get("rubros_distintos", 0) > 1),
        "por_que_no": {k: n for k, n in por_codigo.most_common() if k != "con_rubro"},
        "corte_del_crp": {
            "cargas": cargas,
            "desde": desde.isoformat() if desde else None,
            "hasta": corte.isoformat() if corte else None,
            "nota": ("El CRP cargado cubre una vigencia más las obligaciones "
                     "por pagar de años anteriores. Los contratos de vigencias "
                     "que no se han cargado tienen rubro DESCONOCIDO."),
        },
        "metodo": (
            "Se enlaza el compromiso del CRP con el contrato por (número, "
            "vigencia) de la referencia, y se EXIGE que el documento de la "
            "contraparte coincida con el contratista de SECOP. Sin esa "
            "exigencia, 53 pares medidos atribuían $4.317 millones al contrato "
            "equivocado, porque el Fondo numera convenios, resoluciones y "
            "contratos de servicios en el mismo espacio numérico."),
        "fuente": "CRP de BogData, cargado por pantalla (no es datos abiertos)",
    }
