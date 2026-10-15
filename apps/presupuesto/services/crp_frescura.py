"""¿Está al día el CRP, y qué cuesta que no lo esté?

El CRP de BogData **no se puede automatizar**: es un reporte que alguien
descarga del aplicativo distrital, autenticado, y sube por pantalla. Así que lo
único que el sistema puede hacer es medir su vejez y decir qué se pierde
mientras no llegue — que es la diferencia entre un dato pendiente y un dato que
nadie sabe que falta.

## Dos cosas distintas, y la segunda es la grande

**Vejez del corte vigente.** Medido el 2026-10-15: el corte más reciente es del
5 de octubre, 10 días. Eso está bien.

**Vigencias que NUNCA se cargaron.** Las dos únicas cargas de la historia son
de la vigencia 2026. O sea que 2020, 2021, 2022, 2023, 2024 y 2025 no tienen
CRP, y sus 4.666 contratos no pueden tener rubro ni proyecto del Plan — no por
un defecto del enlace, sino porque el reporte de esas vigencias no existe en la
base. Es lo que convierte «2.084 contratos con rubro» en «2.084 de 5.558»: el
techo no lo pone el método, lo pone lo que falta cargar.

## El umbral, y lo que no se sabe de él

Las dos cargas están a 28 días una de otra (7 de septiembre y 5 de octubre), lo
que sugiere una cadencia mensual. Con DOS observaciones eso no es una cadencia
medida: es una coincidencia de dos fechas. El umbral de 35 días se pone por esa
señal débil y se deja dicho que es débil, para que el día que haya seis cargas
alguien lo recalcule con datos en vez de heredarlo.
"""
import datetime

from django.db import connection

#: Días a partir de los cuales el corte vigente se considera atrasado. Ver el
#: encabezado: la base es UNA sola observación de 28 días entre las dos cargas.
DIAS_AVISO = 35

#: Y a partir de acá, grave: ya pasó más de un ciclo entero sin subir el reporte.
DIAS_GRAVE = 70


def estado(hoy: datetime.date | None = None) -> dict:
    """La frescura del CRP y lo que cuesta, con las dos cosas separadas."""
    hoy = hoy or datetime.date.today()
    with connection.cursor() as cur:
        cur.execute("""
            SELECT vigencia, MAX(fecha_corte), COUNT(*), SUM(filas_leidas)
            FROM crp_carga GROUP BY vigencia ORDER BY vigencia
        """)
        por_vigencia = [
            {"vigencia": v, "ultimo_corte": fc.isoformat() if fc else None,
             "dias": (hoy - fc).days if fc else None,
             "cargas": n, "filas": int(fl or 0)}
            for v, fc, n, fl in cur.fetchall()
        ]
        cur.execute("""
            SELECT anio, COUNT(*), COALESCE(SUM(valor_contrato), 0)
            FROM secop_contrato WHERE anio IS NOT NULL
            GROUP BY anio ORDER BY anio
        """)
        contratos = [(a, n, float(v)) for a, n, v in cur.fetchall()]

    cargadas = {d["vigencia"] for d in por_vigencia}
    faltan = [
        {"vigencia": a, "contratos": n, "valor_cop": v}
        for a, n, v in contratos if a not in cargadas
    ]

    vigente = max((d for d in por_vigencia if d["ultimo_corte"]),
                  key=lambda d: d["ultimo_corte"], default=None)
    dias = vigente["dias"] if vigente else None
    if dias is None:
        nivel = "sin_cargas"
    elif dias >= DIAS_GRAVE:
        nivel = "grave"
    elif dias >= DIAS_AVISO:
        nivel = "atrasado"
    else:
        nivel = "al_dia"

    return {
        "nivel": nivel,
        "corte_vigente": vigente,
        "dias_desde_el_corte": dias,
        "umbral_aviso": DIAS_AVISO,
        "umbral_grave": DIAS_GRAVE,
        "por_vigencia": por_vigencia,
        # Lo que cuesta, en contratos y en plata. Un aviso sin consecuencia
        # medida no lo atiende nadie.
        "vigencias_sin_cargar": faltan,
        "contratos_sin_rubro_por_eso": sum(f["contratos"] for f in faltan),
        "valor_sin_rubro_por_eso_cop": sum(f["valor_cop"] for f in faltan),
        "no_se_puede_automatizar": (
            "El CRP es un reporte que se descarga autenticado del aplicativo "
            "distrital y se sube por pantalla. No hay API: lo único que el "
            "sistema puede hacer es avisar."),
        "donde_se_sube": "/app/plan/matriz",
    }


def resumen_texto(e: dict | None = None) -> list[str]:
    """El estado en líneas, para el log del cron y para un correo."""
    e = e or estado()
    lineas = []
    v = e["corte_vigente"]
    if v:
        lineas.append(
            f"Corte vigente: {v['ultimo_corte']} (vigencia {v['vigencia']}), "
            f"{e['dias_desde_el_corte']} días.")
    else:
        lineas.append("No hay ninguna carga de CRP.")
    if e["nivel"] in ("atrasado", "grave"):
        lineas.append(
            f"ATRASADO: pasó el umbral de {e['umbral_aviso']} días. "
            f"Sube el reporte en {e['donde_se_sube']}.")
    if e["vigencias_sin_cargar"]:
        falt = ", ".join(str(f["vigencia"]) for f in e["vigencias_sin_cargar"])
        lineas.append(
            f"Vigencias SIN CRP: {falt}. Son {e['contratos_sin_rubro_por_eso']:,} "
            f"contratos que no pueden tener rubro ni proyecto del Plan "
            f"(${e['valor_sin_rubro_por_eso_cop']/1e6:,.0f} M contratados).")
    return lineas
