"""Avance de KPI a partir de un evento EJECUTADO.

## Por qué existe

Cinco módulos ya escriben avance desde un hecho suyo —una entrega, una captura,
un acto de festival, un contrato de obra—, cada uno con su propia regla. Lo que
no existía era el camino **genérico**: un evento cualquiera, de cualquier
subgrupo, que reporta lo que entregó. Sin él, la única puerta de entrada para
los otros 17 sectores era el formulario suelto de `/plan/avances`, donde hay que
elegir un KPI entre 77 y escribir un número. Así se llegó a 6 KPIs reportados
de 77.

## De dónde salen los KPIs

De la cadena `evento → actividad_plan → actividad_indicador → indicador`, que
es la que el área controla desde «Actividades SIPSE». **No** de
`evento.indicador_id`.

Esa distinción es el arreglo. El camino viejo —crear el evento con
`indicador_id` y `magnitud_aportada`— tenía tres defectos que juntos explican
por qué nunca produjo nada:

1. **Un solo KPI.** `evento.indicador_id` es singular; una actividad le puede
   sumar a varias metas, y `actividad_indicador` ya lo modela.
2. **Cero contaba como «nada».** El avance se creaba con
   `if data.get("magnitud_aportada")`, y los 9 eventos que traen el campo lo
   traen en `0.0000`. Un reporte de cero ES un reporte —significa «esto no
   entregó»— y es distinto de no haber reportado.
3. **Se escribía al CREAR el evento**, o sea antes de que ocurriera nada.
   Publicar no es ejecutar. Acá el avance se reporta después del hecho, y por
   eso es un acto aparte.

## Idempotencia y reversa

Cada fila se marca con `[evento=<id>][kpi=<id>]` usando `marcador_avance`, que
delimita el valor justamente para que `[kpi=1]` no empareje con `[kpi=11]`.
Volver a reportar ACTUALIZA esa fila; nunca crea una segunda. Revertir borra
las filas marcadas y ninguna otra: los avances `MANUAL` que digitó el área a
mano no los toca nadie desde acá.

## Quién manda cuando dos módulos escriben el mismo KPI

Festivales, Jóvenes, Entregas, Capturas e Infraestructura ya escriben avance a
partir de SU hecho, y sus filas llevan su propio marcador. El evento 90
(«Festival Vallenato») tiene una fila `[festival=7][acto=90]` sobre el KPI 15.
Si la vía genérica escribiera otra fila sobre ese mismo KPI del mismo evento,
el KPI **contaría dos veces el mismo acto**, en silencio y sin que ninguna de
las dos filas se vea mal por separado.

Por eso el bloqueo es **por KPI, no por evento**: un KPI que ya tiene una fila
de otro módulo para este evento queda de solo lectura y dice de quién es; los
demás KPIs de la misma actividad se siguen pudiendo reportar. Bloquear el
evento entero sería más simple y de paso apagaría reportes legítimos.

El dueño se reconoce por lo que la fila NO tiene: si está atada a este evento
y no lleva el marcador `[evento=<id>]`, la escribió otro. Una fila sin
`observaciones` es del formulario viejo de creación de eventos, que escribía
sin marcador ninguno.

## La fecha del aporte es la del hecho, no la del tecleo

Si el evento ya terminó, el avance se fecha el día que terminó. Si sigue
abierto —una actividad anual con `fecha_fin` en diciembre—, se fecha hoy, que
es hasta donde se puede afirmar. De esa fecha sale el `periodo`, que es por
donde se corta el reporte mensual.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.presupuesto.services.marcador_avance import marcador, observaciones

CLAVE_EVENTO = "evento"
CLAVE_KPI = "kpi"


def marca_de(evento_id: int, indicador_id: int) -> str:
    """`[evento=12][kpi=7]` — lo que se escribe y lo que se busca."""
    return marcador(CLAVE_EVENTO, evento_id) + marcador(CLAVE_KPI, indicador_id)


#: Cómo se llama, en pantalla, el módulo dueño de cada marcador.
_DUENOS = {
    "festival": "Festivales",
    "acto": "Festivales",
    "entrega_beca": "Jóvenes a la E",
    "becas_vigencia": "Jóvenes a la E",
    "captura": "capturas del evento",
    "infra_contrato": "seguimiento de Infraestructura",
}


def _dueno_de(observaciones: str) -> str:
    """De `[festival=7][acto=90]` saca «Festivales»."""
    m = re.search(r"\[([a-z_]+)=", observaciones or "")
    if not m:
        # Sin marcador: lo escribió el formulario viejo de creación de eventos,
        # que creaba el avance al CREAR el evento y no dejaba rastro de ello.
        return "el formulario de creación del evento"
    return _DUENOS.get(m.group(1), m.group(1))


def fila_ajena(evento, indicador_id):
    """La fila de avance de este evento+KPI que escribió OTRO módulo, si la hay.

    Es lo que impide contar dos veces el mismo hecho. Ver el docstring del
    módulo: se reconoce porque está atada al evento y NO lleva `[evento=<id>]`.
    """
    from apps.presupuesto.models.indicadores import AvanceIndicador

    for fila in AvanceIndicador.objects.filter(
            evento_id=evento.id, indicador_id=indicador_id, activo=True):
        if marcador(CLAVE_EVENTO, evento.id) not in (fila.observaciones or ""):
            return fila
    return None


def kpis_disponibles(evento):
    """Las relaciones actividad↔KPI a las que este evento le puede sumar."""
    from apps.presupuesto.models.indicadores import ActividadIndicador

    if not evento.actividad_plan_id:
        return []
    return list(
        ActividadIndicador.objects
        .filter(actividad_plan_id=evento.actividad_plan_id, activo=True)
        .select_related("indicador")
        .order_by("indicador__nombre")
    )


def fecha_del_hecho(evento) -> date:
    """La fecha a la que corresponde el avance. Ver el docstring del módulo."""
    hoy = date.today()
    if evento.fecha_fin and evento.fecha_fin <= hoy:
        return evento.fecha_fin
    return hoy


def _bloqueo(evento) -> str | None:
    """Motivo por el que este evento NO puede reportar, o `None` si sí puede."""
    if not evento.actividad_plan_id:
        return ("El evento no está enganchado a una actividad del plan, así que "
                "no hay meta a la cual sumarle. Engánchelo primero.")
    if not kpis_disponibles(evento):
        return ("La actividad del plan no tiene ninguna meta vinculada. "
                "Vincúlela en Plan → Actividades SIPSE y vuelva acá.")
    if evento.fecha_inicio and evento.fecha_inicio > date.today():
        return (f"El evento todavía no empieza (inicia el "
                f"{evento.fecha_inicio.isoformat()}). Publicar no es ejecutar.")
    return None


def reporte_de(evento) -> dict:
    """Qué puede reportar este evento y qué lleva reportado.

    `reportado` es lo que ESTE evento le puso a ese KPI; `acumulado_kpi` es
    todo lo que el KPI lleva de todas las fuentes. Son distintos a propósito:
    sin el segundo no se sabe si el número propio mueve la aguja o no.
    """
    from apps.presupuesto.models.indicadores import AvanceIndicador

    rels = kpis_disponibles(evento)
    kpis = []
    for rel in rels:
        ind = rel.indicador
        fila = (AvanceIndicador.objects
                .filter(indicador_id=ind.id, activo=True,
                        observaciones__contains=marca_de(evento.id, ind.id))
                .order_by("id").first())
        acumulado = sum(
            float(a.magnitud_aportada or 0)
            for a in AvanceIndicador.objects.filter(indicador_id=ind.id, activo=True)
        )
        meta = float(ind.meta_magnitud or 0)
        ajena = fila_ajena(evento, ind.id)
        kpis.append({
            "indicador_id": ind.id,
            "nombre": ind.nombre,
            "unidad_medida": ind.unidad_medida,
            "meta_magnitud": meta,
            "reportado": (float(fila.magnitud_aportada) if fila else None),
            "reportado_en": (fila.fecha_aporte.isoformat()
                             if fila and fila.fecha_aporte else None),
            "periodo": (fila.periodo if fila else None),
            "acumulado_kpi": acumulado,
            "pct_kpi": (round(acumulado / meta * 100, 1) if meta else None),
            # De solo lectura: otro módulo ya reportó este KPI para este
            # evento y escribir acá lo contaría dos veces.
            "editable": ajena is None,
            "dueno": (_dueno_de(ajena.observaciones) if ajena else None),
            "reportado_por_otro": (float(ajena.magnitud_aportada) if ajena else None),
        })
    motivo = _bloqueo(evento)
    return {
        "evento_id": evento.id,
        "evento_nombre": evento.nombre,
        "actividad_plan_id": evento.actividad_plan_id,
        "fecha_del_hecho": fecha_del_hecho(evento).isoformat(),
        "puede_reportar": motivo is None,
        "motivo": motivo,
        "kpis": kpis,
    }


def _a_decimal(valor) -> Decimal:
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"«{valor}» no es un número.")
    if d < 0:
        raise ValueError("La magnitud no puede ser negativa. "
                         "Para deshacer un reporte, retírelo.")
    return d


@transaction.atomic
def reportar(evento, aportes: dict) -> dict:
    """Escribe el avance de este evento. Idempotente por (evento, KPI).

    `aportes` es `{indicador_id: magnitud}`. Un KPI que no esté vinculado a la
    actividad del evento se rechaza: es la garantía de que el vínculo
    actividad↔meta signifique algo y no un adorno.
    """
    from apps.presupuesto.models.indicadores import AvanceIndicador

    motivo = _bloqueo(evento)
    if motivo:
        raise ValueError(motivo)
    if not aportes:
        raise ValueError("No llegó ninguna magnitud que reportar.")

    permitidos = {rel.indicador_id: rel.indicador for rel in kpis_disponibles(evento)}
    fuera = [k for k in aportes if int(k) not in permitidos]
    if fuera:
        raise ValueError(
            f"Estos KPIs no están vinculados a la actividad del evento: "
            f"{', '.join(str(a) for a in fuera)}.")

    # Lo que ya reportó otro módulo no se toca desde acá: sería el mismo hecho
    # contado dos veces. Ver el docstring del módulo.
    for clave in aportes:
        ajena = fila_ajena(evento, int(clave))
        if ajena:
            raise ValueError(
                f"«{permitidos[int(clave)].nombre}» ya lo reporta "
                f"{_dueno_de(ajena.observaciones)} para este evento "
                f"({float(ajena.magnitud_aportada):g}). Ajústelo allá, no acá: "
                f"reportarlo dos veces lo contaría dos veces.")

    cuando = fecha_del_hecho(evento)
    periodo = cuando.strftime("%Y-%m")
    resultado = []
    for clave, valor in aportes.items():
        ind_id = int(clave)
        magnitud = _a_decimal(valor)
        marca = marca_de(evento.id, ind_id)
        fila = (AvanceIndicador.objects
                .filter(indicador_id=ind_id, observaciones__contains=marca)
                .order_by("id").first())
        if fila:
            fila.magnitud_aportada = magnitud
            fila.fecha_aporte = cuando
            fila.periodo = periodo
            fila.origen = "EVENTO"
            fila.activo = True          # revive lo que se hubiera retirado
            fila.evento_id = evento.id
            fila.save(update_fields=["magnitud_aportada", "fecha_aporte",
                                     "periodo", "origen", "activo", "evento"])
            accion = "actualizado"
        else:
            fila = AvanceIndicador.objects.create(
                indicador_id=ind_id, evento_id=evento.id,
                magnitud_aportada=magnitud, fecha_aporte=cuando,
                periodo=periodo, origen="EVENTO",
                observaciones=observaciones(
                    marca, f"reportado desde el evento «{evento.nombre}»"),
            )
            accion = "creado"
        resultado.append({
            "indicador_id": ind_id,
            "nombre": permitidos[ind_id].nombre,
            "magnitud": float(magnitud),
            "accion": accion,
        })
    return {"periodo": periodo, "fecha_aporte": cuando.isoformat(),
            "aportes": resultado}


@transaction.atomic
def revertir(evento, indicador_id: int | None = None) -> int:
    """Retira lo que reportó ESTE evento. Devuelve cuántas filas se retiraron.

    Apaga (`activo=False`) en vez de borrar: el histórico de lo que se reportó
    y luego se deshizo es justamente lo que se audita. Solo toca filas con el
    marcador de este evento, así que los avances `MANUAL` del área quedan
    intactos.
    """
    from apps.presupuesto.models.indicadores import AvanceIndicador

    qs = AvanceIndicador.objects.filter(evento_id=evento.id, activo=True)
    if indicador_id is not None:
        qs = qs.filter(indicador_id=indicador_id,
                       observaciones__contains=marca_de(evento.id, indicador_id))
    else:
        qs = qs.filter(observaciones__contains=marcador(CLAVE_EVENTO, evento.id))
    return qs.update(activo=False)
