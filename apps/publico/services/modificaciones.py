"""Las modificaciones de un contrato: cesiones, prórrogas, adiciones.

## De dónde salen

De `secop_modificacion`, el espejo de dos datasets de SECOP II: 4.304
modificaciones sobre 2.252 de los 3.189 contratos de Kennedy.

## Lo que esta capa dice y no esconde

**«En Edición» es un BORRADOR.** SECOP publica las modificaciones en curso con
ese estado, y leerlas como hechos consumados es afirmar que un contrato cambió
cuando todavía se está redactando el cambio. Cada modificación viaja con su
`estado` y con `en_firme`, que lo resuelve sin que quien consume tenga que
conocer el vocabulario de SECOP.

**`valor_modificacion` es ACUMULADO: es el valor total del contrato vigente en
esa versión, no lo que la modificación movió.** Este docstring afirmaba lo
contrario hasta el 2026-09-30 y era falso; se midió al verificar un hallazgo de
la Oficina de Innovación. La prueba, sobre los 942 contratos con dos o más
modificaciones en firme —los únicos donde las dos hipótesis se distinguen—: el
MÁXIMO del campo coincide con el valor del contrato en 909 (96,5 %) y la SUMA no
coincide **ni una vez** (0 de 942). Lo confirman dos señales más: las 600 filas
en firme de tipo CONCLUSION traen exactamente el valor del contrato —una
conclusión no mueve plata— y el campo viene en cero solo en 1 de 3.777, cuando
un campo de incremento sería cero en toda prórroga.

Por eso se publica además `incremento`, calculado acá por diferencia contra la
modificación anterior en firme. **SECOP no publica el incremento en ninguna
columna**, así que es un derivado nuestro, y en las primeras modificaciones de
cada contrato sale `null` con su motivo: el valor original del contrato tampoco
se publica, así que no hay contra qué restar.

**La cadena se ordena por FECHA, no por `numero_version`.** `numero_version` es
la versión del DOCUMENTO de la modificación —corre de 1 a N mientras pasa de
«En Edición» a «Publicado»—, no la del contrato: hay 258 pares
(contrato, versión) duplicados. Encadenando por versión aparecen 91 bajadas de
valor; por fecha solo 10, y esas 10 son reducciones reales de contrato.

**El contratista ANTERIOR de una cesión no existe en ningún dataset.** No es que
venga vacío: la columna no existe, ni en los tres datasets de modificaciones de
SECOP (35, 5 y 7 columnas) ni en un dataset de cesiones, que no hay en el
catálogo. El contratista NUEVO sí está publicado, pero en otro sitio: es el
`proveedor` del contrato. Se apunta hacia allá en vez de repetirlo.

**El `tipo` de SECOP viene INVERTIDO en el par suspensión/reactivación**, y es
el defecto más grave de esta fuente. Las 185 filas que dicen `SUSPENSIoN` son en
realidad los reinicios —185 de 185, confirmado contra un tercer dataset— y las
suspensiones reales son 291, repartidas entre `REACTIVACIoN`,
`MODIFICACION GENERAL` y `No definido`. Por eso `clases` **no deriva suspensión
ni reactivación de `tipo`**: sale la advertencia y el eje queda sin clasificar
hasta que se ingiera el dataset dedicado. Fechar una suspensión con `tipo` es
fecharla el día en que el contrato se reactivó.
"""
from __future__ import annotations

import unicodedata
from datetime import timedelta

from django.db import connection

#: Estados de SECOP que significan «esto ya pasó». El resto es borrador o
#: trámite: `En Edición` es el caso que más aparece.
_EN_FIRME = {"aprobada", "aprobado", "firmada", "firmado", "publicada", "publicado"}

MOTIVO_SIN_CEDENTE = (
    "Ningún dataset de SECOP publica el contratista ANTERIOR de una cesión: la "
    "columna no existe en los tres datasets de modificaciones ni hay un dataset "
    "de cesiones en el catálogo de datos abiertos. El contrato guarda un solo "
    "proveedor y es el POSTERIOR a la cesión. No se deduce del texto de "
    "`proposito` para no inventar una identidad."
)

MOTIVO_CESIONARIO = (
    "El contratista NUEVO sí está publicado, pero en el contrato y no en la "
    "modificación: es `proveedor` del detalle del contrato, con nombre, "
    "documento y tipo de documento. Se apunta en vez de repetirlo para que no "
    "haya dos copias que puedan discrepar."
)

#: La salvedad del cesionario, y es general a propósito: NO se puede afirmar por
#: fila. `secop_contrato.synced_at` es cuándo sincronizamos NOSOTROS, no cuándo
#: SECOP actualizó el registro, así que no hay forma de comprobar si la fila del
#: contrato se refrescó después de ESTA cesión. Decirlo de todas es honesto;
#: señalar unos cuantos con una fecha que no mide eso, no.
ADVERTENCIA_CESIONARIO = (
    "El contrato guarda UN solo proveedor, el vigente. En un contrato con varias "
    "cesiones, ese proveedor corresponde a la última, no necesariamente a esta. "
    "No podemos verificar por fila si SECOP refrescó el contrato después de esta "
    "cesión: el espejo solo conserva la fecha de NUESTRA sincronización."
)

MOTIVO_SUSPENSION_INVERTIDA = (
    "El `tipo` de SECOP viene invertido en este par y por eso NO se usa: medido "
    "el 2026-10-13 sobre el espejo completo (2020-2026), 1.055 de 1.062 pares "
    "(99,3 %) están al revés — 591 marcados REACTIVACION son suspensiones y "
    "464 marcados SUSPENSION son reanudaciones—. La clase de este eje sale del "
    "dataset DEDICADO de suspensiones (u99c-7mfm), que trae solo dos tipos "
    "limpios. Si esta modificación no quedó clasificada, es que no se encontró "
    "el acto oficial para su fecha."
)

MOTIVO_SUSPENSION_SIN_ACTO = (
    "No hay un acto en el dataset dedicado de suspensiones para este contrato y "
    "esta fecha. El `tipo` de esta fila no se usa como respaldo: está invertido "
    "en el 99,3 % de los casos, y fechar una suspensión con él la fecharía el día "
    "en que el contrato se reactivó."
)

MOTIVO_SUSPENSION_AMBIGUA = (
    "El eje suspensión/reanudación no se publica: en esa misma fecha el "
    "contrato tiene más de una modificación de ese par, y el acto oficial no "
    "dice a cuál de ellas corresponde. Lo único que las distinguiría es el "
    "campo `tipo`, que en esta fuente viene invertido, así que asignarlo "
    "sería adivinar."
)

MOTIVO_ANTICIPADA_INDECIDIBLE = (
    "No se puede decidir si la terminación fue anticipada: la fecha de fin que "
    "trae la modificación y la del contrato difieren en un día por convención "
    "—una es exclusiva y la otra inclusiva—, y la diferencia cae dentro de esa "
    "banda. Un «anticipada: true» en esta franja sería un dato inventado en un "
    "documento con efectos jurídicos."
)

MOTIVO_INCREMENTO_PRIMERA = (
    "Es la primera modificación en firme del contrato y SECOP no publica el "
    "valor original, así que no hay contra qué restar. El incremento no existe "
    "como dato: no es cero."
)

CONVENCION_FIN_MODIFICACION = (
    "EXCLUSIVA — es el día SIGUIENTE al último día de ejecución que registraba "
    "el contrato en ESTA versión de la modificación. Sale del dataset u8cx-r425. "
    "La fecha que gobierna el plazo es `fechas.fin_actual` del contrato, que es "
    "INCLUSIVA. Medido: +1 día en 88,6 % de los contratos, igual en 8,1 %."
)


def _codigo(texto: str | None) -> str | None:
    """`Reactivación`, `REACTIVACIoN` y `REACTIVACION` caen todas en `REACTIVACION`.

    El contrato estable que consume un tercero. El literal del origen viaja
    aparte en `tipo_origen`, para trazabilidad contra datos.gov.co.

    No es un arreglo de codificación: los siete valores de `tipo` del espejo no
    tienen un solo byte no-ASCII —a la Ó no la decodificamos mal, la perdimos—,
    y la fuente hoy ya sirve «Reactivación» correcta. Reexportar la grafía de
    SECOP rompería al consumidor cada vez que el origen la cambie, y acaba de
    cambiarla.
    """
    if not texto:
        return None
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c))
    return "_".join(sin_tildes.upper().split()) or None


_SQL = """
    SELECT identificador, id_contrato, tipo, estado, descripcion, proposito,
           fecha_aprobacion, fecha_creacion, fecha_inicio_contrato,
           fecha_fin_contrato, dias_extendidos, valor_modificacion,
           numero_version
    FROM secop_modificacion
    WHERE id_contrato = ANY(%s)
    ORDER BY id_contrato,
             COALESCE(fecha_aprobacion, fecha_creacion) NULLS LAST,
             identificador
"""

#: Los actos de suspensión/reanudación del dataset DEDICADO. Es la ÚNICA
#: fuente de ese eje: el `tipo` de `secop_modificacion` está invertido en el
#: 99,3 % de los casos (1.055 de 1.062 pares medidos sobre 2020-2026).
_SQL_SUSPENSION = """
    SELECT id_contrato, tipo_codigo, fecha_aprobacion, fecha_creacion, proposito
    FROM secop_suspension
    WHERE id_contrato = ANY(%s)
    ORDER BY id_contrato, COALESCE(fecha_aprobacion, fecha_creacion), id
"""

#: El contexto del contrato que hace falta para los derivados: el desfase de
#: fechas, el fin pactado y la decisión de «anticipada».
_SQL_CONTRATO = """
    SELECT id_contrato, fecha_fin, COALESCE(dias_adicionados, 0)
    FROM secop_contrato
    WHERE id_contrato = ANY(%s)
"""


def _iso(d):
    return d.isoformat() if d else None


def _fila(r) -> dict:
    (ident, id_ct, tipo, estado, descripcion, proposito, f_aprob, f_crea,
     f_ini, f_fin, dias, valor, version) = r
    codigo = _codigo(tipo)
    es_cesion = codigo == "CESION"
    return {
        "identificador": ident,
        # El contrato estable. Cablearse acá, no al literal.
        "tipo_codigo": codigo,
        # El literal de la fuente, para contrastar contra datos.gov.co.
        "tipo_origen": tipo,
        # Alias de `tipo_codigo` por un ciclo. Se retira: usar `tipo_codigo`.
        "tipo": codigo,
        "estado": estado,
        # Resuelto acá y no en cada consumidor: «En Edición» es un borrador.
        "en_firme": (estado or "").strip().lower() in _EN_FIRME,
        "descripcion": descripcion,
        "proposito": proposito,
        "fecha_aprobacion": _iso(f_aprob),
        "fecha_creacion": _iso(f_crea),
        # Las fechas del contrato DESPUÉS de esta modificación.
        "contrato_fecha_inicio": _iso(f_ini),
        "contrato_fecha_fin": _iso(f_fin),
        "contrato_fecha_fin_convencion": CONVENCION_FIN_MODIFICACION,
        # Ya restada, para que no la reste cada consumidor y se equivoque uno.
        "contrato_fecha_fin_inclusiva": _iso(f_fin - timedelta(days=1)) if f_fin else None,
        "dias_extendidos": dias,
        # ACUMULADO: el valor del contrato vigente en esta versión. Ver el
        # docstring del módulo. `incremento` lo agrega `por_contrato()`.
        "valor_modificacion": float(valor) if valor is not None else None,
        "valor_modificacion_convencion": (
            "ACUMULADO — es el valor TOTAL del contrato vigente en esta versión, "
            "no lo que la modificación movió. No sumar entre modificaciones. El "
            "derivado está en `incremento`."),
        "numero_version": version,
        "numero_version_nota": (
            "Es la versión del DOCUMENTO de la modificación, no la del contrato: "
            "se repite entre modificaciones del mismo contrato. Para encadenar, "
            "ordenar por `fecha_aprobacion`."),
        # La cesión: el cedente no existe, el cesionario sí pero en el contrato.
        "cedente": None,
        "cedente_motivo": MOTIVO_SIN_CEDENTE if es_cesion else None,
        "cesionario_en": "contrato.proveedor" if es_cesion else None,
        "cesionario_motivo": MOTIVO_CESIONARIO if es_cesion else None,
        "cesionario_advertencia": ADVERTENCIA_CESIONARIO if es_cesion else None,
        # Se conservan un ciclo porque el consumidor ya los lee. Siempre null.
        "proveedor_anterior": None,
        "proveedor_nuevo": None,
        "proveedores_motivo": MOTIVO_SIN_CEDENTE if es_cesion else None,
    }


def _clasificar(m: dict, delta, fin_pactado, acto_oficial=None,
                ambiguo: bool = False) -> None:
    """Las clases de UNA modificación. Es una LISTA: 8,9 % son de dos a la vez.

    La combinación más común es adición + prórroga (208 casos), así que un campo
    único obligaría a botar la mitad del hecho.

    Cada clase viaja con la señal que la disparó: una clase que no se puede
    auditar no sirve en un documento con efectos jurídicos.
    """
    clases, motivos = [], {}

    if m["tipo_codigo"] == "CESION":
        clases.append("cesion")
        motivos["cesion"] = "tipo_codigo=CESION"

    # La señal que más rescata, y no es el tipo: da prórroga en 1.952 filas,
    # 1.617 de ellas donde el tipo no nombra nada.
    if (m["dias_extendidos"] or 0) > 0:
        clases.append("prorroga")
        motivos["prorroga"] = f"dias_extendidos={m['dias_extendidos']}"

    if delta is not None and delta > 0:
        clases.append("adicion")
        motivos["adicion"] = f"delta_valor=+{delta:.0f}"
    elif delta is not None and delta < 0:
        clases.append("reduccion")
        motivos["reduccion"] = f"delta_valor={delta:.0f}"

    if m["tipo_codigo"] == "CONCLUSION":
        clases.append("terminacion")
        motivos["terminacion"] = "tipo_codigo=CONCLUSION"

    m["clases"] = clases
    m["clases_motivo"] = motivos or None

    # EL EJE SUSPENSIÓN/REANUDACIÓN SALE DEL DATASET DEDICADO, nunca del `tipo`.
    #
    # Hasta el 2026-10-13 este eje quedaba sin clasificar y con una advertencia,
    # porque el `tipo` de SECOP viene invertido: medido emparejando por contrato
    # y fecha, 1.055 de 1.062 pares (99,3 %) están al revés. Se resuelve con
    # `u99c-7mfm`, que trae solo dos tipos limpios, y la clase se acompaña del
    # propósito oficial para que se pueda auditar leyéndolo.
    en_eje = m["tipo_codigo"] in ("SUSPENSION", "REACTIVACION")
    # El acto oficial se empareja por contrato + fecha, y en una misma fecha
    # puede haber más de una modificación: el 2024-05-14 un contrato tiene a la
    # vez una SUSPENSIoN y una CESION, y el acto oficial de ese día es la
    # reanudación. Sin esta condición la cesión también quedaba marcada como
    # reanudación — 128 filas de otro tipo contagiadas, medido. El eje solo
    # puede caer sobre una fila que YA es de ese par.
    if en_eje and ambiguo:
        m["suspension_proposito_oficial"] = None
        m["clases_advertencia"] = MOTIVO_SUSPENSION_AMBIGUA
    elif acto_oficial and en_eje:
        clase = ("suspension" if acto_oficial["tipo_codigo"] == "SUSPENSION"
                 else "reanudacion")
        if clase not in clases:
            clases.append(clase)
        motivos[clase] = f"dataset_oficial=u99c-7mfm:{acto_oficial['tipo_codigo']}"
        m["clases"] = clases
        m["clases_motivo"] = motivos
        m["suspension_proposito_oficial"] = acto_oficial.get("proposito")
        # Se dice cuando el tipo del espejo CONTRADICE al oficial: es el dato
        # que permite a quien consume entender por qué su propio filtro por
        # `tipo` le daba otra cosa.
        esperado = ("SUSPENSION" if m["tipo_codigo"] == "SUSPENSION"
                    else "REANUDACION")
        m["clases_advertencia"] = (
            None if acto_oficial["tipo_codigo"] == esperado
            else MOTIVO_SUSPENSION_INVERTIDA)
    else:
        m["suspension_proposito_oficial"] = None
        m["clases_advertencia"] = MOTIVO_SUSPENSION_SIN_ACTO if en_eje else None

    if not clases:
        m["no_determinada_motivo"] = (
            "No hay señal que permita clasificarla: ni el tipo la nombra, ni el "
            "plazo se movió, ni hay valor anterior contra el que comparar."
            if delta is None else
            "No hay señal que permita clasificarla: el tipo no la nombra y ni "
            "el plazo ni el valor se movieron.")
    else:
        m["no_determinada_motivo"] = None

    # «Anticipada» en TRES estados. Las 763 CONCLUSION no son terminaciones
    # anticipadas: se aprueban una mediana de 356 días DESPUÉS del fin pactado,
    # o sea que son el cierre administrativo. Se decide solo con evidencia.
    if "terminacion" not in clases:
        m["anticipada"] = None
        m["anticipada_motivo"] = None
        return
    fin_mod = m["contrato_fecha_fin"]
    if not fin_mod or not fin_pactado:
        m["anticipada"] = None
        m["anticipada_motivo"] = (
            "Falta una de las dos fechas que habría que comparar.")
        return
    from datetime import date
    dm = date.fromisoformat(fin_mod)
    dias = (dm - fin_pactado).days
    if dias < -1:
        m["anticipada"] = True
        m["anticipada_motivo"] = (
            f"La terminación deja el fin {abs(dias)} días antes del pactado.")
    elif dias > 1:
        m["anticipada"] = False
        m["anticipada_motivo"] = (
            f"El fin avanzó {dias} días respecto del pactado: es cierre, no "
            "terminación anticipada.")
    else:
        m["anticipada"] = None
        m["anticipada_motivo"] = MOTIVO_ANTICIPADA_INDECIDIBLE


def por_contrato(ids: list[str]) -> dict[str, list]:
    """Las modificaciones de varios contratos, agrupadas. Dos consultas.

    Los derivados que se calculan acá y no por fila, porque necesitan la cadena
    completa del contrato: `incremento`, `es_ultima_en_firme` y
    `desfase_dias_vs_fin_actual`.
    """
    if not ids:
        return {}
    with connection.cursor() as cur:
        cur.execute(_SQL, [ids])
        filas = cur.fetchall()
        cur.execute(_SQL_CONTRATO, [ids])
        ctx = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        # Los actos oficiales del eje suspensión/reanudación, indexados por
        # (contrato, fecha) para emparejarlos con la modificación que les
        # corresponde. Se indexa por las DOS fechas porque el espejo de
        # modificaciones a veces trae solo la de creación.
        cur.execute(_SQL_SUSPENSION, [ids])
        actos: dict[tuple, dict] = {}
        for id_ct, cod, f_apr, f_cre, prop in cur.fetchall():
            a = {"tipo_codigo": cod, "proposito": prop}
            for f in (f_apr, f_cre):
                if f is not None:
                    actos.setdefault((id_ct, f.isoformat()), a)

    salida: dict[str, list] = {}
    for r in filas:
        salida.setdefault(r[1], []).append(_fila(r))

    for id_ct, mods in salida.items():
        fin_actual, dias_adic = ctx.get(id_ct, (None, 0))
        # El fin PACTADO: el vigente menos lo que se adicionó.
        fin_pactado = (fin_actual - timedelta(days=dias_adic)
                       if fin_actual else None)

        # La cadena del incremento, SOLO entre las que están en firme y en
        # orden cronológico. Un borrador no mueve el valor del contrato.
        # Fechas en las que este contrato tiene DOS modificaciones del par:
        # 17 casos medidos. Ahí el acto oficial no dice a cuál pertenece.
        _del_par = [x for x in mods
                    if x["tipo_codigo"] in ("SUSPENSION", "REACTIVACION")]
        _cuenta: dict = {}
        for x in _del_par:
            f = x["fecha_aprobacion"] or x["fecha_creacion"]
            _cuenta[f] = _cuenta.get(f, 0) + 1
        fechas_dobles = {(id_ct, f) for f, n in _cuenta.items() if n > 1}

        anterior = None
        for m in mods:
            delta = None
            if m["en_firme"]:
                v = m["valor_modificacion"]
                if v is not None and anterior is not None:
                    delta = v - anterior
                if v is not None:
                    anterior = v
            # El acto oficial de ESTA modificación, buscado por su fecha.
            fecha_m = m["fecha_aprobacion"] or m["fecha_creacion"]
            acto = actos.get((id_ct, fecha_m)) if fecha_m else None
            ambiguo = (id_ct, fecha_m) in fechas_dobles

            m["incremento"] = delta
            m["incremento_motivo"] = (
                MOTIVO_INCREMENTO_PRIMERA
                if delta is None and m["en_firme"] else
                ("No aplica: es un borrador y no movió el valor del contrato."
                 if not m["en_firme"] else None))
            _clasificar(m, delta, fin_pactado, acto, ambiguo)

            # El desfase contra la fecha que de verdad gobierna el plazo.
            if m["contrato_fecha_fin"] and fin_actual:
                from datetime import date
                m["desfase_dias_vs_fin_actual"] = (
                    date.fromisoformat(m["contrato_fecha_fin"]) - fin_actual).days
            else:
                m["desfase_dias_vs_fin_actual"] = None

        # Cuál es la ÚLTIMA en firme, con criterio cronológico. Lo marcamos
        # nosotros porque elegirla por `numero_version` produce 65 casos de
        # desfase por encima de +1 donde el criterio por fecha produce cero: de
        # ahí salía la mitad de los atípicos que reportó el consumidor.
        for m in mods:
            m["es_ultima_en_firme"] = False
        firmes = [m for m in mods if m["en_firme"]]
        if firmes:
            firmes[-1]["es_ultima_en_firme"] = True

    return salida


def resumen(mods: list[dict] | None) -> dict:
    """Lo que cabe en la ficha del contrato sin desplegar la lista entera."""
    mods = mods or []
    firmes = [m for m in mods if m["en_firme"]]

    def _n(clase):
        return sum(1 for m in firmes if clase in (m.get("clases") or []))

    ultima = next((m for m in mods if m.get("es_ultima_en_firme")), None)
    return {
        "total": len(mods),
        "en_firme": len(firmes),
        # Se cuentan aparte porque son las que cambian QUIÉN ejecuta.
        "cesiones": _n("cesion"),
        "prorrogas": _n("prorroga"),
        "adiciones": _n("adicion"),
        "reducciones": _n("reduccion"),
        "terminaciones": _n("terminacion"),
        "no_determinadas": sum(1 for m in firmes if not (m.get("clases") or [])),
        "dias_extendidos": sum(m["dias_extendidos"] or 0 for m in firmes) or None,
        "borradores": len(mods) - len(firmes),
        "borradores_nota": (
            "Modificaciones que SECOP publica en estado de edición o trámite. "
            "No son cambios en firme." if len(mods) - len(firmes) else None),
        # Para el valor del certificado NO se suma: es el de la última en firme.
        "valor_vigente": ultima["valor_modificacion"] if ultima else None,
        "valor_vigente_fuente": (
            "Valor de la última modificación en firme (`es_ultima_en_firme`). "
            "NO sumar `valor_modificacion`: es acumulado."),
        # Cuál fecha manda, dicho en la ficha para que no haya que deducirlo.
        "fin_vigente_fuente": "contrato.fechas.fin_actual",
    }
