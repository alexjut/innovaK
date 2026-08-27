"""El motor de la Formulación: transiciones, completitud y semáforo.

Tres cosas que este repo NO tenía y por eso se escriben acá una sola vez:

1. **Una máquina de estados de verdad.** Los cinco intentos que hay en el
   repositorio validan la ACCIÓN pero nunca el estado de ORIGEN, así que hoy se
   puede saltar de «borrador» a «validada» sin pasar por «enviada». Acá la
   transición se comprueba contra `formulacion_transicion`, que es una TABLA:
   la pregunta «¿se puede pasar de A a B?» tiene una respuesta y está en el
   dato, no repartida en `if`s.

2. **Completitud con bloqueo.** Decisión de Alex del 2026-08-27, y respeta la
   del 24: no hay peso. Los cuatro estados son los mismos del expediente y
   `no_aplica` queda FUERA del denominador — la diferencia entre medir y
   castigar. El rigor lo pone `bloquea`: un requisito crítico que falta impide
   pasar a contratación aunque el porcentaje vaya alto.

3. **El semáforo**, que copia la REGLA del muro y no su fórmula: si no hay con
   qué calificar, no se califica. Un vacío no se pinta de rojo.

Nada de acá sabe de HTTP. Los tres gates —scope, rol y pertenencia— los pone la
vista, igual que en `CapturarDatoContratoView`.
"""
from __future__ import annotations

#: Los cuatro estados de un requisito. Mismos nombres que en el motor de
#: completitud del expediente, a propósito: un usuario que ya entendió «no
#: aplica» en una pantalla no tiene que volver a entenderlo en otra.
OK, PENDIENTE, SIN_DATO, NO_APLICA = "ok", "pendiente", "sin_dato", "no_aplica"

#: Semáforo. El color NUNCA va solo: cada estado lleva su etiqueta escrita
#: (WCAG 1.4.1), igual que el resto de los tableros del proyecto.
SEMAFORO = {
    "lista":       ("🟢", "Lista para contratación"),
    "en_proceso":  ("🟡", "En proceso"),
    "observada":   ("🟠", "Con observaciones"),
    "bloqueada":   ("🔴", "Bloqueada"),
    "sin_iniciar": ("⚪", "Sin iniciar"),
}


class TransicionInvalida(ValueError):
    """El estado destino no es alcanzable desde el actual. Lleva el motivo en
    castellano porque termina en pantalla."""


def catalogo_estados() -> list[dict]:
    """Los estados, en orden. Para pintar el stepper y para validar."""
    from apps.presupuesto.models import EstadoFormulacion
    return [{"codigo": e.codigo, "nombre": e.nombre, "orden": e.orden,
             "descripcion": e.descripcion, "es_final": e.es_final,
             "bloquea_contratacion": e.bloquea_contratacion}
            for e in EstadoFormulacion.objects.all()]


def destinos_validos(estado_codigo: int) -> list[dict]:
    """A qué estados se puede pasar desde éste. Sale de la tabla, no de código.

    Viaja al frontend para que la pantalla ofrezca SÓLO lo posible. Es la misma
    razón por la que `puede_registrar_etapa` viaja en el payload del
    expediente: si la UI reimplementa la regla, hay dos fuentes de verdad y la
    del navegador se puede editar.
    """
    from apps.presupuesto.models import EstadoFormulacion, TransicionFormulacion
    codigos = list(TransicionFormulacion.objects
                   .filter(origen_id=estado_codigo)
                   .values_list("destino_id", flat=True))
    return [{"codigo": e.codigo, "nombre": e.nombre}
            for e in EstadoFormulacion.objects.filter(codigo__in=codigos)]


def completitud(formulacion) -> dict:
    """Qué le falta a una formulación, y si está bloqueada.

    LA FÓRMULA: `ok / aplicables`, donde aplicables excluye `no_aplica`. Plana,
    sin pesos — decisión de Alex del 2026-08-24 sobre el motor del expediente,
    que aquí se respeta: «cualquier ponderación es una opinión disfrazada de
    número».

    LO QUE BLOQUEA no es el porcentaje: es que falte un requisito marcado
    `bloquea`. Por eso una formulación puede ir al 90 % y no poder pasar a
    contratación, que es exactamente lo que pide el §12 del plan.

    Un requisito del catálogo que la formulación todavía no tiene registrado
    cuenta como `sin_dato` —no se omite—, porque «nadie lo ha mirado» y «no
    aplica» son cosas distintas y sólo la segunda sale del denominador.
    """
    from apps.presupuesto.models import RequisitoCumplido, RequisitoFormulacion

    catalogo = list(RequisitoFormulacion.objects.filter(activo=True))
    marcados = {r.requisito_id: r for r in
                RequisitoCumplido.objects.filter(formulacion=formulacion)
                .select_related("requisito")}

    filas, ok, aplicables, faltan_criticos = [], 0, 0, []
    # Cuántos requisitos ha MIRADO alguien. Distinto de cuántos están en `ok`:
    # sirve para no calificar el silencio (ver `semaforo`).
    revisados = 0
    for req in catalogo:
        marca = marcados.get(req.codigo)
        estado = marca.estado if marca else SIN_DATO
        if marca is not None:
            revisados += 1
        aplica = estado != NO_APLICA
        if aplica:
            aplicables += 1
            if estado == OK:
                ok += 1
            elif req.bloquea:
                faltan_criticos.append(req.nombre)
        filas.append({
            "codigo": req.codigo, "nombre": req.nombre, "bloque": req.bloque,
            "orden": req.orden, "estado": estado,
            "obligatorio": req.obligatorio, "bloquea": req.bloquea,
            "exige_evidencia": req.exige_evidencia,
            "tiene_evidencia": bool(marca and marca.documento_id),
            "observacion": marca.observacion if marca else None,
        })

    # `null`, NUNCA 0: sin requisitos aplicables no es que esté al 0 %, es que
    # no hay nada que medir. Un 0 % ahí acusaría a un área de no haber hecho
    # algo que nadie le pidió.
    pct = round(ok / aplicables * 100) if aplicables else None

    return {
        "pct": pct,
        "ok": ok,
        "aplicables": aplicables,
        "no_aplica": len(catalogo) - aplicables,
        "revisados": revisados,
        "de": len(catalogo),
        "bloqueada": bool(faltan_criticos),
        "faltan_criticos": faltan_criticos,
        "requisitos": sorted(filas, key=lambda f: (f["orden"], f["codigo"])),
    }


def semaforo(formulacion, datos_completitud: dict | None = None) -> dict:
    """El color de una formulación, con su etiqueta y su motivo.

    Copia la REGLA del semáforo del muro, no su fórmula: **si no hay con qué
    calificar, no se califica**. Una formulación recién creada sale «sin
    iniciar» en gris, nunca en rojo — el gris es tarea pendiente, no reproche.
    """
    from apps.presupuesto.models import EstadoFormulacion

    c = datos_completitud or completitud(formulacion)
    estado = formulacion.estado

    if formulacion.cancelado_en is not None:
        clave, motivo = "sin_iniciar", "Cancelada: no continuará el proceso."
    elif not estado.bloquea_contratacion:
        clave, motivo = "lista", "Terminó la formulación y puede contratarse."
    elif not c["revisados"]:
        # EL SILENCIO NO SE CALIFICA. Una formulación que nadie ha tocado no
        # está «bloqueada»: no ha empezado. Pintarla de rojo acusaría a un área
        # de incumplir algo que todavía no le tocaba hacer — es la misma regla
        # que el muro aplica con los subgrupos sin datos.
        clave, motivo = "sin_iniciar", "Todavía no se ha diligenciado ningún requisito."
    elif c["bloqueada"]:
        clave = "bloqueada"
        motivo = ("Falta un requisito crítico: "
                  + ", ".join(c["faltan_criticos"]) + ".")
    elif estado.codigo == _codigo_de("Con observaciones"):
        clave, motivo = "observada", "La revisión dejó correcciones pendientes."
    else:
        clave, motivo = "en_proceso", f"En «{estado.nombre}»."

    icono, etiqueta = SEMAFORO[clave]
    return {"clave": clave, "icono": icono, "etiqueta": etiqueta, "motivo": motivo}


def _codigo_de(nombre: str) -> int | None:
    from apps.presupuesto.models import EstadoFormulacion
    return (EstadoFormulacion.objects.filter(nombre=nombre)
            .values_list("codigo", flat=True).first())


def cambiar_estado(formulacion, destino_codigo, usuario, observacion=None) -> dict:
    """Mueve una formulación de estado. Lanza `TransicionInvalida` si no se puede.

    Tres guardas, y ninguna sobra:

    1. **La transición existe en la tabla.** Sin esto se puede llegar a
       «Lista para contratación» desde «Borrador», que es el agujero que tienen
       hoy los otros dominios del repo.
    2. **El estado actual no es final.** De «Cancelada» no se sale: reabrir una
       formulación cancelada sin dejar rastro borraría el motivo por el que se
       canceló.
    3. **No se pasa a contratación con un requisito crítico pendiente.** Es la
       frontera del §10: `bloquea_contratacion=False` sólo se alcanza si la
       completitud lo permite.

    Todo queda auditado con `registrar_cambio`, y la auditoría va DENTRO de la
    misma transacción que el UPDATE.
    """
    from django.db import transaction
    from django.utils import timezone

    from apps.presupuesto.models import EstadoFormulacion
    from apps.presupuesto.models.auditoria import AuditoriaDato
    from apps.presupuesto.services.auditoria import registrar_cambio

    actual = formulacion.estado
    destino = EstadoFormulacion.objects.filter(codigo=destino_codigo).first()
    if destino is None:
        validos = ", ".join(f"{e['codigo']}={e['nombre']}" for e in catalogo_estados())
        raise TransicionInvalida(f"Ese estado no existe. Los válidos son: {validos}.")

    if actual.es_final:
        raise TransicionInvalida(
            f"La formulación está «{actual.nombre}» y de ahí no se sale.")

    posibles = {d["codigo"] for d in destinos_validos(actual.codigo)}
    if destino.codigo not in posibles:
        nombres = ", ".join(d["nombre"] for d in destinos_validos(actual.codigo))
        raise TransicionInvalida(
            f"No se puede pasar de «{actual.nombre}» a «{destino.nombre}». "
            f"Desde «{actual.nombre}» sólo: {nombres or 'ningún estado'}.")

    if not destino.bloquea_contratacion:
        c = completitud(formulacion)
        if c["bloqueada"]:
            raise TransicionInvalida(
                "No puede pasar a contratación: falta "
                + ", ".join(c["faltan_criticos"]) + ".")

    ahora = timezone.now()
    with transaction.atomic():
        formulacion.estado = destino
        formulacion.estado_fecha = ahora
        formulacion.estado_usuario_id = getattr(usuario, "id", None)
        formulacion.actualizado_en = ahora
        formulacion.save(update_fields=["estado", "estado_fecha",
                                        "estado_usuario", "actualizado_en"])
        registrar_cambio(
            usuario=usuario, entidad="formulacion", entidad_id=formulacion.id,
            campo="estado", valor_anterior=actual.nombre, valor_nuevo=destino.nombre,
            proyecto_id=formulacion.actividad_plan.proyecto_id,
            subgrupo_id=formulacion.subgrupo_id,
            fuente=AuditoriaDato.MANUAL, observacion=observacion)

    return {"codigo": destino.codigo, "nombre": destino.nombre,
            "fecha": ahora.isoformat(),
            "destinos": destinos_validos(destino.codigo)}
