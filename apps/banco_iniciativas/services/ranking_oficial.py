"""Persistencia y ranking de la MATRIZ OFICIAL (Documento Maestro 2026-07-29).

`matriz_oficial.py` es puro a propósito: calcula y no escribe. Este módulo es el
que lo baja a la base y arma el orden de adjudicación.

CÓMO SE GUARDA EN UN SCHEMA QUE NACIÓ PARA OTRA MATRIZ
------------------------------------------------------
`banco_evaluacion_inscripcion` se diseñó para el modelo viejo (65 automáticos +
35 de comité + 5 de bono). La matriz oficial no tiene comité ni bono, así que el
mapeo es este y NO requiere DDL:

    puntaje_auto    ← el total de los 100 puntos (todo es automático)
    puntaje_comite  ← NULL   (el Documento Maestro elimina el comité)
    bono_genero     ← 0      (los 5 puntos se absorbieron en el criterio 9)
    total           ← igual a puntaje_auto
    auto_detalle    ← el desglose completo por criterio (JSONB, auditable)
    rubrica_version ← "oficial-2026-07-29"

Que `rubrica_version` diga cuál motor escribió la fila es lo que permite
distinguir una evaluación oficial de una del motor viejo sin adivinar por el
valor: `es_oficial(ev)` es la única forma correcta de preguntarlo.

Las columnas del comité (`viabilidad_cumple`, `ambiental_cumple`,
`innovacion_cumple`, `bono_mujeres`) se dejan en NULL. No se borran: las filas
del motor viejo son evidencia de cómo se evaluó el piloto y se conservan hasta
que Deportes diga otra cosa.
"""
import logging

from django.db import transaction
from django.utils import timezone

from apps.banco_iniciativas.models import (
    BancoEvaluacionInscripcion,
    BancoRubrica,
    InscripcionBancoIniciativa,
)
from apps.banco_iniciativas.services.matriz_oficial import (
    CUPOS_ADJUDICABLES,
    MATRIZ_VERSION,
    POLITICA_CUPOS_INSUFICIENTES,
    PUNTAJE_MINIMO_ADJUDICABLE,
    REGLA_DESEMPATE,
    calcular_matriz_oficial,
    snapshot_rubrica,
)

log = logging.getLogger(__name__)

#: Estado de la evaluación cuando la calcula la matriz oficial. No hay paso
#: intermedio de comité: se calcula y queda en firme.
ESTADO_CALCULADA = "calculada"


def es_oficial(ev):
    """True si esa fila de evaluación la escribió la matriz oficial."""
    return bool(ev) and ev.rubrica_version == MATRIZ_VERSION


def detalle_oficial(ev):
    """El `auto_detalle` de una evaluación, siempre como dict.

    OJO: la columna es JSONB y las dos matrices guardan cosas distintas. El
    motor viejo guarda una **lista** de criterios; la matriz oficial guarda el
    **dict** completo del cálculo. Hacer `.get()` a ciegas revienta con
    `AttributeError: 'list' object has no attribute 'get'` en cuanto el evento
    tiene una fila del motor anterior — que es el estado de hoy.
    """
    detalle = getattr(ev, "auto_detalle", None)
    return detalle if isinstance(detalle, dict) else {}


@transaction.atomic
def activar_rubrica_oficial():
    """Registra la matriz oficial en `banco_rubrica` y la deja como la activa.

    NO es opcional: `banco_evaluacion_inscripcion.rubrica_version` tiene FK a
    `banco_rubrica.version`, así que sin esta fila ninguna evaluación oficial
    se puede guardar (falla con ForeignKeyViolation). Idempotente.

    Las versiones anteriores quedan congeladas con `activa=False` — no se
    borran: son la única forma de releer cómo se evaluó el piloto de mayo.
    """
    obj, creada = BancoRubrica.objects.get_or_create(
        version=MATRIZ_VERSION,
        defaults={
            "nombre": "Matriz Oficial — Documento Maestro Deportes 2026-07-29",
            "config": snapshot_rubrica(),
            "activa": True,
        },
    )
    if not creada:
        # Al reactivar se refresca el snapshot: si Deportes ratificó una
        # decisión, la config congelada tiene que reflejar lo que corre hoy.
        obj.config = snapshot_rubrica()
        obj.activa = True
        obj.save(update_fields=["config", "activa"])
    BancoRubrica.objects.exclude(version=MATRIZ_VERSION).update(activa=False)
    return obj


@transaction.atomic
def guardar_evaluacion_oficial(insc):
    """Calcula la matriz oficial de una inscripción y la persiste. Idempotente.

    Devuelve la `BancoEvaluacionInscripcion` ya guardada. Recalcular sobre una
    fila del motor viejo la SOBREESCRIBE con el resultado oficial y limpia los
    campos de comité, que en el modelo nuevo no existen.
    """
    activar_rubrica_oficial()   # la FK de rubrica_version exige que exista

    calc = calcular_matriz_oficial(insc)
    total = calc["total"]

    ev, _creada = BancoEvaluacionInscripcion.objects.get_or_create(
        inscripcion_id=insc.id,
        defaults={"rubrica_version": MATRIZ_VERSION},
    )
    ev.rubrica_version = MATRIZ_VERSION
    ev.puntaje_auto = total
    ev.puntaje_comite = None
    ev.bono_genero = 0
    ev.total = total
    ev.auto_detalle = calc
    ev.estado = ESTADO_CALCULADA
    ev.caracterizacion_at = timezone.now()
    ev.finalizado_at = timezone.now()
    # El comité ya no existe: si la fila venía del motor viejo, estas cuatro
    # columnas quedarían mintiendo sobre cómo se calculó el total.
    ev.viabilidad_cumple = None
    ev.ambiental_cumple = None
    ev.innovacion_cumple = None
    ev.bono_mujeres = None
    ev.save()
    return ev


def _clave_orden(fila):
    """Orden de adjudicación: total ↓, Bloque 2 ↓, radicación ↑, id ↑.

    Los tres primeros son REGLA_DESEMPATE. El `id` es el cierre técnico y no
    es decorativo: `created_at` tiene por defecto `now()`, que en PostgreSQL
    devuelve la hora de **inicio de la transacción** — dos filas escritas en la
    misma transacción comparten el timestamp al microsegundo. Medido el
    2026-08-10 con 6 postulaciones de prueba: sin este desempate el orden lo
    resolvía el motor de la base, o sea al azar, justo en la frontera donde se
    decide quién recibe cuánto. El id de la secuencia es monótono, así que
    conserva el orden de radicación cuando el reloj no alcanza.
    """
    ev, insc = fila
    bloque2 = (detalle_oficial(ev).get("bloque2") or {}).get("pts") or 0
    # Se niegan los dos ascendentes para poder ordenar todo descendente de una
    # sola pasada, sin depender del orden en que la BD devuelva las filas.
    radicado = insc.created_at.timestamp() if insc.created_at else float("inf")
    return (float(ev.total or 0), float(bloque2), -radicado, -insc.id)


@transaction.atomic
def recalcular_lote_oficial(evento_id, asignar_ranking=True):
    """Recalcula con la matriz oficial TODAS las inscripciones de un evento.

    Devuelve un resumen con lo que hace falta para leer el resultado sin
    malinterpretarlo: cuántas se procesaron, cuántas vienen del formulario
    anterior y cuántas quedan dentro de los cupos.
    """
    inscripciones = list(
        InscripcionBancoIniciativa.objects.filter(evento_id=evento_id)
    )
    filas = [(guardar_evaluacion_oficial(insc), insc) for insc in inscripciones]

    resumen = {
        "evento_id": evento_id,
        "procesadas": len(filas),
        "version": MATRIZ_VERSION,
        "formulario_anterior": sum(
            1 for ev, _ in filas
            if detalle_oficial(ev).get("formulario_anterior")
        ),
    }
    if asignar_ranking:
        resumen.update(asignar_ranking_evento(evento_id, _filas=filas))
    return resumen


@transaction.atomic
def asignar_ranking_evento(evento_id, cupos=None, _filas=None):
    """Numera el ranking (1-based) de las evaluaciones OFICIALES de un evento.

    Solo entran filas escritas por la matriz oficial: mezclar en un mismo orden
    un total de 100 puntos con uno de 105 daría un ranking sin significado. Las
    del motor viejo quedan con `ranking_pos = NULL`.
    """
    cupos = CUPOS_ADJUDICABLES if cupos is None else cupos

    if _filas is None:
        inscripciones = {
            i.id: i for i in
            InscripcionBancoIniciativa.objects.filter(evento_id=evento_id)
        }
        evaluaciones = BancoEvaluacionInscripcion.objects.filter(
            inscripcion_id__in=inscripciones.keys())
        _filas = [(ev, inscripciones[ev.inscripcion_id]) for ev in evaluaciones]

    oficiales = [f for f in _filas if es_oficial(f[0])]
    otras = [f for f in _filas if not es_oficial(f[0])]

    oficiales.sort(key=_clave_orden, reverse=True)
    for posicion, (ev, _insc) in enumerate(oficiales, start=1):
        ev.ranking_pos = posicion
    for ev, _insc in otras:
        ev.ranking_pos = None

    todas = [ev for ev, _ in oficiales] + [ev for ev, _ in otras]
    if todas:
        BancoEvaluacionInscripcion.objects.bulk_update(todas, ["ranking_pos"])

    return {
        "rankeadas": len(oficiales),
        "sin_rankear": len(otras),
        "cupos": cupos,
        "adjudicables": min(len(oficiales), cupos),
        "cupos_insuficientes": len(oficiales) < cupos,
        "politica_cupos_insuficientes": POLITICA_CUPOS_INSUFICIENTES,
        "regla_desempate": REGLA_DESEMPATE,
    }


def entra_en_cupos(ranking_pos, total_oficiales, cupos=None):
    """¿Esa posición queda adjudicada?

    Con postulaciones suficientes es simplemente `pos <= cupos`. Si llegaron
    menos que los cupos manda `POLITICA_CUPOS_INSUFICIENTES` (decisión 3 de
    Deportes): o entran todas, o solo las que superen el puntaje mínimo — y en
    ese caso la posición no alcanza para responder, así que devuelve None y
    quien pregunte tiene que mirar el puntaje.
    """
    cupos = CUPOS_ADJUDICABLES if cupos is None else cupos
    if ranking_pos is None:
        return False
    if total_oficiales >= cupos:
        return ranking_pos <= cupos
    if POLITICA_CUPOS_INSUFICIENTES == "adjudicar_todas":
        return True
    return None   # "puntaje_minimo": lo decide el puntaje, no la posición


def adjudicada(ev, total_oficiales, cupos=None):
    """Resuelve `entra_en_cupos` hasta un booleano, aplicando el puntaje mínimo."""
    veredicto = entra_en_cupos(ev.ranking_pos, total_oficiales, cupos)
    if veredicto is None:
        return float(ev.total or 0) >= PUNTAJE_MINIMO_ADJUDICABLE
    return veredicto
