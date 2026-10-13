"""Los períodos de suspensión de un contrato, armados con los actos oficiales.

El dataset dedicado (`u99c-7mfm`, espejado en `secop_suspension`) publica ACTOS
—una suspensión, una reanudación—, no períodos. El período hay que armarlo
emparejando actos consecutivos, y por eso se publica como ESTIMADO con su
método a la vista: no es un campo del origen.

## Por qué no se puede usar `secop_modificacion`

El `tipo` de esa tabla viene invertido en el par: 94,1 % de los casos medidos.
Armar el período con él pondría el inicio de la suspensión el día del reinicio.
Ver `modificaciones.MOTIVO_SUSPENSION_INVERTIDA`.

## Lo que se midió antes de escribir esto (2026-10-13, 941 actos / 352 contratos)

    períodos cerrados (suspensión → reanudación) ....... 304 en 257 contratos
    cadenas que quedan abiertas ........................ 113
    reanudaciones sin suspensión previa ................  70
    suspensiones sobre una suspensión ya abierta ....... 150
    duración: mínimo 0 · mediana 9 · máximo 213 días
    de 0 días (el acto y su cierre el mismo día) .......   7

Las formas más comunes de la secuencia son `SR` (101 contratos), `S` sola (54),
`SS` (40), `SSR` (39) y `SRR` (24). O sea: encadenar de a pares y confiar en
que vengan limpios habría fallado en la mitad de los contratos.

## El contraste independiente

`secop_contrato.estado_contrato` trae «Suspendido» en 116 contratos. Nuestra
cadena deja 113 abiertas, y **106 coinciden** — 91,4 % desde el lado de SECOP,
93,8 % desde el nuestro—. Eso es una comprobación de verdad: dos caminos
distintos, uno derivado de actos y otro un campo publicado, llegan al mismo
contrato.

Los 17 que no coinciden NO se resuelven acá, se declaran. Los 10 en que SECOP
dice suspendido y la cadena cierra tienen todos la misma forma: el último día
trae una suspensión Y una reanudación, y el orden dentro del mismo día no está
en el dato. Elegir uno sería inventar el estado actual de un contrato.

## Lo que el período NO es

No es la duración de la suspensión. Es la distancia entre dos actos
administrativos. El término lo decreta el texto del acto —«desde el 18 de
septiembre inclusive y hasta el 1 de octubre inclusive», 13 días— y ese mismo
contrato tiene sus dos actos a 5 días de distancia. Sobre los 197 períodos
comparables, el texto difiere en 142 (72,1 %), entre -21 y +36 días. Por eso no
se publica ningún total de días y el campo se llama `dias_entre_actos`.

## Lo que nunca se afirma

«Está suspendido HOY». De los 113 contratos con la cadena abierta, 111 tienen
`fecha_fin` ya pasada: SECOP deja el estado en «Suspendido» después de que el
plazo venció. Lo que se publica es el hecho —el último acto publicado es una
suspensión del día tal— y el contraste con el campo de SECOP.
"""
from __future__ import annotations

from django.db import connection

#: Dataset del que sale cada acto. Viaja en la respuesta para que el consumidor
#: pueda ir a verificarlo sin preguntarnos.
FUENTE = "u99c-7mfm"

METODO = (
    "Período ESTIMADO: no existe en el origen. Se arma emparejando actos "
    "oficiales consecutivos del dataset dedicado de suspensiones "
    f"({FUENTE}), ordenados por fecha de aprobación —y por fecha de creación "
    "cuando falta—. Una suspensión abre el período y la siguiente reanudación "
    "lo cierra; una suspensión sobre un período ya abierto se cuenta como "
    "prórroga de esa suspensión y NO abre uno nuevo, para no partir en dos un "
    "mismo hecho."
)

#: LA advertencia de este frente. El período entre actos NO es la suspensión
#: que el acto decretó, y la diferencia no es un detalle: medido el 2026-10-13
#: sobre los 197 períodos comparables, el texto del propio acto decreta fechas
#: distintas en 142 (72,1 %), con diferencias de -21 a +36 días. Un acto dice
#: «se suspende desde el 18 de septiembre inclusive y hasta el 1 de octubre
#: inclusive» —13 días— mientras sus dos actos están fechados con 5 días de
#: separación. Publicar 5 como duración de esa suspensión sería falso.
MOTIVO_DIAS_ENTRE_ACTOS = (
    "`dias_entre_actos` es la distancia entre el acto que suspende y el acto "
    "que reanuda. NO es la duración de la suspensión: el término lo decreta el "
    "texto del acto, y medido sobre 197 períodos comparables difiere en 72,1 % "
    "de los casos, entre -21 y +36 días. El término decretado está en "
    "`proposito_inicio`, que viaja completo para poder leerlo."
)

MOTIVO_MISMO_DIA = (
    "El período cierra el mismo día en que abre. El dataset no publica la hora, "
    "así que 0 días no es una duración medida: es «el acto y su cierre están "
    "fechados el mismo día»."
)

MOTIVO_REANUDACION_SUELTA = (
    "Hay reanudaciones sin una suspensión previa que cerrar. Se cuentan y no se "
    "usan: lo más probable es que la suspensión correspondiente sea anterior al "
    "alcance del espejo, o que no esté publicada."
)

MOTIVO_DISCREPA_CERRADA = (
    "SECOP marca el contrato como «Suspendido», pero la cadena de actos cierra. "
    "No se decide a favor de ninguno de los dos: en los 10 casos medidos el "
    "último día trae una suspensión Y una reanudación, y el orden dentro del "
    "mismo día no está en el dato."
)

MOTIVO_DISCREPA_ABIERTA = (
    "La cadena de actos queda abierta, pero SECOP no marca el contrato como "
    "«Suspendido». Se publica el hecho —el último acto es una suspensión— y la "
    "discrepancia, sin resolverla."
)

NOTA_NO_ES_HOY = (
    "Una cadena abierta NO dice que el contrato esté suspendido hoy: de los 113 "
    "contratos con la cadena abierta, 111 tienen `fecha_fin` ya pasada. SECOP "
    "deja el estado en «Suspendido» después de que el plazo venció."
)

_SQL = """
    SELECT id_contrato, tipo_codigo,
           COALESCE(fecha_aprobacion, fecha_creacion) AS efectiva,
           fecha_aprobacion, proposito
    FROM secop_suspension
    WHERE id_contrato = ANY(%s)
      AND COALESCE(fecha_aprobacion, fecha_creacion) IS NOT NULL
    ORDER BY id_contrato, efectiva, id
"""

_SQL_ESTADO = """
    SELECT id_contrato, estado_contrato, fecha_fin
    FROM secop_contrato
    WHERE id_contrato = ANY(%s)
"""


def _vacio(estado: str | None, fecha_fin) -> dict:
    """La respuesta de un contrato SIN un solo acto oficial.

    No es lo mismo que «no estuvo suspendido»: es «el dataset dedicado no tiene
    actos para este contrato». Si además SECOP lo marca suspendido, eso se dice.
    """
    suspendido_en_secop = (estado or "").strip().lower() == "suspendido"
    return {
        "periodos": [],
        "abierta": None,
        "dias_suspendido_total": None,
        "dias_motivo": ("Sin actos en el dataset dedicado. No significa cero "
                        "días de suspensión: significa que no hay con qué "
                        "decirlo."),
        "estado_secop": estado,
        "discrepancia": (MOTIVO_DISCREPA_CERRADA if suspendido_en_secop else None),
        "reanudaciones_sin_suspension": 0,
        "metodo": METODO,
        "fuente": FUENTE,
    }


def periodos(ids: list[str]) -> dict[str, dict]:
    """Los períodos de suspensión de esos contratos, uno por contrato.

    Devuelve SIEMPRE una entrada por cada id pedido, incluso sin actos: un
    contrato ausente del resultado se lee como «no hay dato» cuando lo que pasa
    es que no se preguntó, y esa confusión ya costó un diagnóstico entero.
    """
    if not ids:
        return {}
    ids = list(dict.fromkeys(ids))
    with connection.cursor() as cur:
        cur.execute(_SQL_ESTADO, [ids])
        estados = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        cur.execute(_SQL, [ids])
        actos: dict[str, list] = {}
        for id_ct, cod, efectiva, f_apr, prop in cur.fetchall():
            actos.setdefault(id_ct, []).append(
                {"tipo": cod, "fecha": efectiva, "aprobada": f_apr is not None,
                 "proposito": prop})

    salida: dict[str, dict] = {}
    for id_ct in ids:
        estado, fecha_fin = estados.get(id_ct, (None, None))
        propios = actos.get(id_ct)
        if not propios:
            salida[id_ct] = _vacio(estado, fecha_fin)
            continue
        salida[id_ct] = _armar(propios, estado, fecha_fin)
    return salida


def _armar(propios: list[dict], estado: str | None, fecha_fin) -> dict:
    """El recorrido. Una suspensión abre, una reanudación cierra.

    Una segunda suspensión sobre un período ya abierto NO abre otro: en los
    datos aparece 150 veces y es una prórroga de la misma suspensión. Partirla
    en dos períodos inventaría una reanudación que nunca ocurrió.
    """
    cerrados: list[dict] = []
    sueltas = 0
    abierta_desde = None
    prorrogas = 0
    textos: list[str] = []

    for a in propios:
        if a["tipo"] == "SUSPENSION":
            if abierta_desde is None:
                abierta_desde = a["fecha"]
                prorrogas = 0
                textos = [a["proposito"]] if a["proposito"] else []
            else:
                prorrogas += 1
                if a["proposito"]:
                    textos.append(a["proposito"])
        else:
            if abierta_desde is None:
                sueltas += 1
                continue
            cerrados.append({
                "inicio": abierta_desde.isoformat(),
                "fin": a["fecha"].isoformat(),
                "dias_entre_actos": (a["fecha"] - abierta_desde).days,
                "dias_entre_actos_motivo": MOTIVO_DIAS_ENTRE_ACTOS,
                "mismo_dia_motivo": (MOTIVO_MISMO_DIA
                                     if a["fecha"] == abierta_desde else None),
                "prorrogas_de_la_suspension": prorrogas,
                "proposito_inicio": textos[0] if textos else None,
                "proposito_fin": a["proposito"],
            })
            abierta_desde = None
            prorrogas = 0
            textos = []

    suspendido_en_secop = (estado or "").strip().lower() == "suspendido"
    abierta = None
    discrepancia = None
    if abierta_desde is not None:
        abierta = {
            "desde": abierta_desde.isoformat(),
            "prorrogas_de_la_suspension": prorrogas,
            "proposito": textos[0] if textos else None,
            "concuerda_con_estado_secop": suspendido_en_secop,
            "nota": NOTA_NO_ES_HOY,
        }
        if not suspendido_en_secop:
            discrepancia = MOTIVO_DISCREPA_ABIERTA
    elif suspendido_en_secop:
        discrepancia = MOTIVO_DISCREPA_CERRADA

    # NO se publica un total de días suspendidos. Sería la suma de distancias
    # entre actos administrativos, que difiere del término decretado en 72 % de
    # los casos: un número con cara de duración que no mide una duración. Quien
    # necesite el plazo tiene que leer el texto de cada acto, y por eso viaja.
    return {
        "periodos": cerrados,
        "abierta": abierta,
        "dias_suspendido_total": None,
        "dias_motivo": (
            "No se publica: sería la suma de distancias entre actos "
            "administrativos, y el término que decreta el acto difiere en "
            "72,1 % de los casos medidos. Ver `dias_entre_actos_motivo`."),
        "estado_secop": estado,
        "discrepancia": discrepancia,
        "reanudaciones_sin_suspension": sueltas,
        "reanudaciones_sin_suspension_motivo": (MOTIVO_REANUDACION_SUELTA
                                                if sueltas else None),
        "metodo": METODO,
        "fuente": FUENTE,
    }
