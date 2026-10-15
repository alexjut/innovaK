"""Las observaciones de una revisión: qué se observó, dónde, y si se resolvió.

Antes del DDL 039, «Con observaciones» era solo un estado y el texto —si
acaso— iba en el campo `observacion` de la auditoría del cambio de estado: una
sola cadena para todo lo que el revisor tuviera que decir. Con eso, devolver una
formulación era un gesto: el formulador recibía un estado y un párrafo, y nadie
podía comprobar después qué se corrigió.

## El ciclo, y quién mueve cada paso

    abierta      la escribió el revisor
    respondida   la contestó el formulador — NO la cierra él
    atendida     el revisor aceptó la respuesta
    desestimada  el revisor la retiró, con motivo

Cerrar no es del mismo que responde. Si el formulador pudiera marcar
«atendida», la observación sería un trámite: se contesta cualquier cosa y se
cierra sola. Es la misma separación que gobierna las transiciones (DDL 037).

## Nunca se borra

No hay función de borrado acá, y no debe haberla. Una observación es la razón
por la que una formulación volvió atrás; borrarla deja el expediente diciendo
que el camino fue recto. Lo que sobra se DESESTIMA, y la desestimación exige
motivo.

Las Historias lo piden textual: «permite marcar observaciones como atendidas
sin eliminarlas».

## Las dos compuertas que hacen que esto sirva

1. **No se puede devolver «con observaciones» sin observar nada.** Si se
   pudiera, el estado afirmaría que hay observaciones y el formulador no
   tendría qué corregir.
2. **No se puede reenviar a revisión con observaciones sin responder.** Si se
   pudiera, el revisor volvería a encontrar lo mismo y la devolución no habría
   servido de nada.

Las dos viven en `cambiar_estado` como guardas, igual que el carril.
"""
from django.db import connection, transaction
from django.utils import timezone

ABIERTA = "abierta"
RESPONDIDA = "respondida"
ATENDIDA = "atendida"
DESESTIMADA = "desestimada"

#: Las que todavía piden algo de alguien.
PENDIENTES = (ABIERTA, RESPONDIDA)

#: Mínimo de texto. No es un capricho: una observación de tres letras no le
#: dice al formulador qué corregir, y el CHECK de la tabla lo exige igual.
MINIMO_TEXTO = 10


class ObservacionInvalida(ValueError):
    pass


def _carril_de(usuario) -> str | None:
    from apps.login.services.permisos import CARRILES_FORMULACION, tiene_carril
    for carril in CARRILES_FORMULACION:
        if tiene_carril(usuario, carril):
            return carril
    return None


def listar(formulacion_id: int) -> list[dict]:
    """Todas, incluidas las cerradas. El historial es el punto."""
    with connection.cursor() as cur:
        cur.execute("""
            SELECT o.id, o.seccion, o.requisito_codigo, o.campo, o.texto,
                   o.autor_id, o.autor_carril, o.creado_en,
                   o.respuesta, o.respondida_por_id, o.respondida_en,
                   o.estado, o.cerrada_por_id, o.cerrada_en, o.cierre_motivo,
                   r.nombre
            FROM formulacion_observacion o
            LEFT JOIN formulacion_requisito r ON r.codigo = o.requisito_codigo
            WHERE o.formulacion_id = %s
            ORDER BY o.creado_en, o.id
        """, [formulacion_id])
        return [{
            "id": f[0], "seccion": f[1], "requisito_codigo": f[2],
            "requisito_nombre": f[15], "campo": f[3], "texto": f[4],
            "autor_id": f[5], "autor_carril": f[6],
            "creado_en": f[7].isoformat() if f[7] else None,
            "respuesta": f[8], "respondida_por_id": f[9],
            "respondida_en": f[10].isoformat() if f[10] else None,
            "estado": f[11], "cerrada_por_id": f[12],
            "cerrada_en": f[13].isoformat() if f[13] else None,
            "cierre_motivo": f[14],
            "pendiente": f[11] in PENDIENTES,
        } for f in cur.fetchall()]


def resumen(formulacion_id: int) -> dict:
    """Cuántas hay en cada estado. Es lo que alimenta las compuertas."""
    with connection.cursor() as cur:
        cur.execute("""SELECT estado, COUNT(*) FROM formulacion_observacion
                       WHERE formulacion_id = %s GROUP BY 1""", [formulacion_id])
        por_estado = dict(cur.fetchall())
    return {
        "por_estado": por_estado,
        "total": sum(por_estado.values()),
        "abiertas": por_estado.get(ABIERTA, 0),
        "respondidas": por_estado.get(RESPONDIDA, 0),
        "pendientes": sum(por_estado.get(e, 0) for e in PENDIENTES),
        "cerradas": (por_estado.get(ATENDIDA, 0)
                     + por_estado.get(DESESTIMADA, 0)),
    }


def crear(formulacion, usuario, texto, seccion=None, requisito_codigo=None,
          campo=None) -> dict:
    """Una observación nueva. La escribe quien revisa, no quien formula.

    Un formulador observando su propia formulación no es una observación: es una
    nota, y para eso está la descripción. Si el formulador pudiera observar,
    podría además cerrar su propia observación respondiéndola, y la compuerta
    del reenvío dejaría de significar algo.
    """
    texto = (texto or "").strip()
    if len(texto) < MINIMO_TEXTO:
        raise ObservacionInvalida(
            f"La observación necesita al menos {MINIMO_TEXTO} caracteres: el "
            f"formulador tiene que poder saber qué corregir.")
    carril = _carril_de(usuario)
    if carril is None:
        raise ObservacionInvalida("No pertenece a ningún carril de revisión.")
    if carril == "formulador" and not getattr(usuario, "is_superuser", False):
        raise ObservacionInvalida(
            "Las observaciones las escribe quien revisa. El formulador "
            "responde; para sus propias notas está la descripción.")
    if requisito_codigo:
        with connection.cursor() as cur:
            cur.execute("""SELECT bloque FROM formulacion_requisito
                           WHERE codigo = %s AND activo""", [requisito_codigo])
            fila = cur.fetchone()
        if fila is None:
            raise ObservacionInvalida("Ese requisito no está en el catálogo.")
        # La sección se deduce del requisito si no la mandaron: así no pueden
        # discrepar.
        seccion = seccion or fila[0]

    with transaction.atomic(), connection.cursor() as cur:
        cur.execute("""
            INSERT INTO formulacion_observacion
                (formulacion_id, seccion, requisito_codigo, campo, texto,
                 autor_id, autor_carril, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, [formulacion.id, seccion, requisito_codigo or None,
              (campo or None), texto, usuario.id, carril, ABIERTA])
        obs_id = cur.fetchone()[0]
    _auditar(formulacion, usuario, f"observacion:{obs_id}", None, texto[:200])
    return {"id": obs_id, "estado": ABIERTA}


def responder(formulacion, obs_id: int, usuario, respuesta: str) -> dict:
    """El formulador contesta. NO la cierra: eso es del revisor."""
    respuesta = (respuesta or "").strip()
    if len(respuesta) < MINIMO_TEXTO:
        raise ObservacionInvalida(
            f"La respuesta necesita al menos {MINIMO_TEXTO} caracteres.")
    obs = _una(formulacion.id, obs_id)
    if obs["estado"] not in (ABIERTA, RESPONDIDA):
        raise ObservacionInvalida(
            f"Esa observación está «{obs['estado']}» y ya no admite respuesta.")
    from apps.login.services.permisos import puede_crear_en_area
    if not puede_crear_en_area(usuario, formulacion.subgrupo_id):
        raise ObservacionInvalida(
            "Responder una observación es del formulador de esta área.")
    ahora = timezone.now()
    with transaction.atomic(), connection.cursor() as cur:
        cur.execute("""
            UPDATE formulacion_observacion
               SET respuesta = %s, respondida_por_id = %s, respondida_en = %s,
                   estado = %s
             WHERE id = %s AND formulacion_id = %s
        """, [respuesta, usuario.id, ahora, RESPONDIDA, obs_id, formulacion.id])
    _auditar(formulacion, usuario, f"observacion:{obs_id}:respuesta",
             obs["estado"], respuesta[:200])
    return {"id": obs_id, "estado": RESPONDIDA}


def cerrar(formulacion, obs_id: int, usuario, resultado: str,
           motivo: str | None = None) -> dict:
    """El revisor acepta la respuesta o retira la observación.

    `desestimada` exige motivo, y eso no es burocracia: retirar una observación
    sin decir por qué es indistinguible de borrarla, que es lo que no se puede
    hacer.
    """
    if resultado not in (ATENDIDA, DESESTIMADA):
        raise ObservacionInvalida(
            f"El cierre es «{ATENDIDA}» o «{DESESTIMADA}».")
    obs = _una(formulacion.id, obs_id)
    if obs["estado"] in (ATENDIDA, DESESTIMADA):
        raise ObservacionInvalida("Esa observación ya está cerrada.")
    carril = _carril_de(usuario)
    if carril is None or (carril == "formulador"
                          and not getattr(usuario, "is_superuser", False)):
        raise ObservacionInvalida(
            "Cerrar una observación es de quien revisa. Si fuera de quien "
            "responde, la observación sería un trámite.")
    motivo = (motivo or "").strip() or None
    if resultado == DESESTIMADA and (not motivo or len(motivo) < MINIMO_TEXTO):
        raise ObservacionInvalida(
            "Desestimar exige motivo: sin él, retirar una observación es "
            "indistinguible de borrarla.")
    if resultado == ATENDIDA and obs["estado"] != RESPONDIDA:
        raise ObservacionInvalida(
            "No se puede dar por atendida una observación que nadie respondió.")
    ahora = timezone.now()
    with transaction.atomic(), connection.cursor() as cur:
        cur.execute("""
            UPDATE formulacion_observacion
               SET estado = %s, cerrada_por_id = %s, cerrada_en = %s,
                   cierre_motivo = %s
             WHERE id = %s AND formulacion_id = %s
        """, [resultado, usuario.id, ahora, motivo, obs_id, formulacion.id])
    _auditar(formulacion, usuario, f"observacion:{obs_id}:cierre",
             obs["estado"], resultado)
    return {"id": obs_id, "estado": resultado}


def _una(formulacion_id: int, obs_id: int) -> dict:
    for o in listar(formulacion_id):
        if o["id"] == obs_id:
            return o
    raise ObservacionInvalida("Esa observación no existe en esta formulación.")


def _auditar(formulacion, usuario, campo, antes, despues) -> None:
    from apps.presupuesto.models.auditoria import AuditoriaDato
    from apps.presupuesto.services.auditoria import registrar_cambio
    registrar_cambio(
        usuario=usuario, entidad="formulacion", entidad_id=formulacion.id,
        campo=campo, valor_anterior=antes, valor_nuevo=despues,
        proyecto_id=formulacion.actividad_plan.proyecto_id,
        subgrupo_id=formulacion.subgrupo_id, fuente=AuditoriaDato.MANUAL)
