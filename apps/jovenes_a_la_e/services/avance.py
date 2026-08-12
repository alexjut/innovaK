"""Avance de los KPI de becas — recálculo por (indicador, vigencia).

## Por qué no se parece al patrón J2

El patrón que usan los demás módulos suma **una fila de avance por cada hecho**
(una entrega, una captura, un acto). Acá no sirve, por tres razones que salieron
del dato real:

1. **La unidad es la PERSONA, no la matrícula.** Una persona puede tener dos
   matrículas en la misma vigencia (verificado: el documento 1000494673). Sumar
   filas la contaría dos veces en una meta que habla de jóvenes impactados.

2. **La meta es de cuatrienio y el archivo llega por vigencia.** Sumar sin
   distinguir el año mezcla ejecuciones de vigencias distintas en el mismo
   número.

3. **Acceso y permanencia son metas distintas.** El patrón viejo escribía la
   misma magnitud a TODOS los indicadores de la actividad, así que un
   beneficiario con los dos cumplimientos le sumaba 2 al KPI de acceso *y* 2 al
   de permanencia. Acá cada cumplimiento va al indicador que le corresponde.

Por eso el avance no se ACUMULA: se **recalcula**. Una sola fila por
(indicador, vigencia), y su magnitud es

    COUNT(DISTINCT persona) de las entregas VALIDADAS de esa vigencia
    que tienen el cumplimiento de ESE indicador

Recalcular en vez de sumar hace que sea idempotente por construcción —correrlo
diez veces da lo mismo que correrlo una— y que no dependa de ningún marcador de
texto dentro de `observaciones`, que es de donde salió el defecto que se cerró
el 2026-08-12.

## Lo que NUNCA toca

Solo escribe filas `origen='EVENTO'` del indicador y periodo que le
corresponden. Los avances `MANUAL` los digita el área a mano y borrarlos sería
destruir trabajo humano sin dejar rastro; hay tres de Infraestructura en la base
que este servicio no puede rozar.

## El acumulado del cuatrienio NO es la suma de las vigencias

Si una persona recibe acceso en 2025 y permanencia en 2026, cuenta una vez en
cada meta y eso está bien: son metas distintas. Pero si apareciera con el mismo
cumplimiento en dos vigencias, sumar las filas anuales la contaría dos veces
contra una meta que habla de jóvenes. Por eso `acumulado_cuatrienio()` lo
calcula con su propio DISTINCT sobre todo el período, y no sumando lo anual.
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction

logger = logging.getLogger(__name__)

#: Qué cumplimiento alimenta a qué meta.
META_ACCESO = "23771"
META_PERMANENCIA = "23772"
CAMPO_POR_META = {
    META_ACCESO: "cumplimiento_acceso",
    META_PERMANENCIA: "cumplimiento_permanencia",
}


def meta_de_indicador(indicador) -> str | None:
    """A qué meta corresponde un KPI: se lee del código en su nombre o descripción.

    No hay columna que lo diga —`presu_indicador_meta_proyecto` no guarda el
    código de meta— y las metas 23771/23772 no existen como filas propias en
    `metas`: la única que hay es un stub. Así que el vínculo se declara donde sí
    se puede escribir y queda a la vista de quien administre el KPI: su nombre.

    Si un KPI no nombra ninguna de las dos, devuelve None y el recálculo lo
    trata como un indicador general — recibe a todos los beneficiarios de la
    vigencia, sin discriminar cumplimiento.
    """
    texto = f"{indicador.nombre or ''} {indicador.descripcion or ''}"
    for meta in (META_ACCESO, META_PERMANENCIA):
        if meta in texto:
            return meta
    return None


def _personas_de(vigencia: int, meta: str | None) -> int:
    """Personas DISTINTAS con ese cumplimiento en esa vigencia."""
    from apps.jovenes_a_la_e.models import EntregaBeca

    qs = EntregaBeca.objects.filter(vigencia=vigencia, estado="validada")
    campo = CAMPO_POR_META.get(meta or "")
    if campo:
        qs = qs.filter(**{campo: True})
    # `.order_by()` NO es decorativo: `EntregaBeca` declara
    # `Meta.ordering = ['-created_at','-id']`, y Django mete esas columnas en el
    # SELECT de un `.values(...).distinct()`. El DISTINCT pasa a ser sobre
    # (documento, created_at, id) y CUENTA MATRÍCULAS, no personas. Hoy da igual
    # por casualidad —cada persona quedó con una sola matrícula— pero el modelo
    # admite dos, que es justamente lo que estos conteos vinieron a distinguir.
    return qs.order_by().values("numero_documento").distinct().count()


@transaction.atomic
def recalcular(vigencia: int, *, actividad_plan_id: int) -> dict:
    """Deja el avance de esa vigencia igual a lo que dicen los datos. Idempotente."""
    from apps.presupuesto.models import ActividadIndicador, AvanceIndicador

    periodo = f"{int(vigencia)}-12"      # la vigencia es anual: se cierra en diciembre
    resultado = {"periodo": periodo, "indicadores": [], "motivo": None}

    relaciones = list(ActividadIndicador.objects
                      .filter(actividad_plan_id=actividad_plan_id, activo=True)
                      .select_related("indicador"))
    if not relaciones:
        resultado["motivo"] = (
            "La actividad no tiene ningún KPI vinculado: no hay a qué sumarle. "
            "Cree el indicador de la meta y vuelva a recalcular.")
        return resultado

    for rel in relaciones:
        ind = rel.indicador
        meta = meta_de_indicador(ind)
        magnitud = _personas_de(vigencia, meta)

        # SOLO filas EVENTO de este indicador y periodo. Un filtro más ancho se
        # llevaría por delante los avances MANUAL que digita el área.
        fila = (AvanceIndicador.objects
                .filter(indicador_id=ind.id, periodo=periodo, origen="EVENTO")
                .order_by("id").first())
        if fila is None:
            AvanceIndicador.objects.create(
                indicador_id=ind.id, magnitud_aportada=magnitud,
                fecha_aporte=date(int(vigencia), 12, 31), periodo=periodo,
                origen="EVENTO",
                observaciones=_marca(vigencia, meta, magnitud))
            accion = "creado"
        else:
            fila.magnitud_aportada = magnitud
            fila.observaciones = _marca(vigencia, meta, magnitud)
            fila.save(update_fields=["magnitud_aportada", "observaciones", "updated_at"])
            accion = "actualizado"

        resultado["indicadores"].append({
            "indicador_id": ind.id, "nombre": ind.nombre, "meta": meta,
            "personas": magnitud, "accion": accion,
        })

    if all(i["personas"] == 0 for i in resultado["indicadores"]):
        resultado["motivo"] = (
            "Ninguna entrega de esta vigencia tiene marcado el cumplimiento de "
            "acceso o permanencia, así que el avance queda en cero. El archivo "
            "del área no trae esa discriminación: se marca con "
            "`marcar_cumplimiento_cargue` o mandando el archivo con la columna.")
    return resultado


def _marca(vigencia: int, meta: str | None, magnitud: int) -> str:
    from apps.presupuesto.services.marcador_avance import marcador, observaciones
    return observaciones(
        marcador("becas_vigencia", vigencia),
        f"{magnitud} personas distintas"
        + (f" · meta {meta}" if meta else " · sin discriminar meta"))


def acumulado_cuatrienio(*, meta: str | None = None) -> dict:
    """Personas distintas en TODO el período, que no es la suma de las vigencias.

    Quien recibe el mismo beneficio dos años seguidos es una persona, no dos.
    Sumar las filas anuales lo contaría doble contra una meta que habla de
    jóvenes impactados.
    """
    from apps.jovenes_a_la_e.models import EntregaBeca

    qs = EntregaBeca.objects.filter(estado="validada")
    campo = CAMPO_POR_META.get(meta or "")
    if campo:
        qs = qs.filter(**{campo: True})
    # Ver la nota de `_personas_de`: sin `.order_by()` el DISTINCT cuenta
    # matrículas en vez de personas, que es exactamente lo que esta función
    # existe para no hacer.
    qs = qs.order_by()
    por_vigencia = {}
    for vig in qs.values_list("vigencia", flat=True).distinct():
        por_vigencia[vig] = (qs.filter(vigencia=vig)
                             .values("numero_documento").distinct().count())
    return {
        "personas_distintas": qs.values("numero_documento").distinct().count(),
        "por_vigencia": por_vigencia,
        "suma_de_vigencias": sum(por_vigencia.values()),
    }
