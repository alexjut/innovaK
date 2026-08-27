"""Siembra como Formulación lo que el área YA está formulando en el plan.

    docker exec innova_k python manage.py sembrar_formulaciones_existentes            # seco
    docker exec innova_k python manage.py sembrar_formulaciones_existentes --write

SECO POR DEFECTO. E idempotente en el sentido estricto —la segunda corrida no
duplica ni pisa nada—, pero OJO con leer eso como «mantiene al día»: **sólo
siembra la PRIMERA vigencia de cada actividad**. Cuando llegue 2027, la
formulación de ese año la abre el área desde la pantalla; este comando dirá «ya
existía» y no hará nada. Es un sembrador de arranque, no un sincronizador.

QUÉ SIEMBRA, Y POR QUÉ ESAS. Las actividades del plan que **tienen indicador y
no tienen contrato**: son las que el área está formulando ahora mismo y que
hasta hoy no tenían dónde vivir. Medido el 2026-08-27: son seis, cinco de
Cultura y el Banco de Iniciativas Recreodeportivas de Deporte — el caso que
Alex puso como ejemplo («no está en SECOP pero sí es un contrato que se está
armando»).

EL DISCRIMINADOR ES «TIENE INDICADOR», no `actividad_id`. Parecía que
`actividad_id IS NULL` separaba las líneas del plan de las disciplinas
deportivas, y es falso: el Banco (#108) tiene `actividad_id` y es una línea del
plan. Las 34 disciplinas —Boxeo, Polimotor, ARTES ESCÉNICAS— no tienen
indicador ni contrato, y quedan fuera.

LO QUE NO SE INVENTA:

  · **La vigencia sale de la mejor fuente que haya**, y el comando dice de cuál
    salió cada una (ver `SQL_CANDIDATAS`). Para las seis da 2026, y lo bueno es
    que llegan por TRES caminos independientes: la #113 por `festival.vigencia`,
    que es un año DECLARADO; la #108 por las fechas de su `meta_proyecto`; y las
    cuatro de Cultura por su evento vivo más antiguo. Si una actividad no
    tuviera ninguna fuente, NO se siembra: se reporta y lo dice el área.

    ⚠️ **Por qué importa el orden.** Los eventos de las cuatro de Cultura se
    crearon con `fecha_inicio = date.today()` desde un script de siembra
    (`scripts/seed_actividades_cultura_2026_06_09.py:70`), así que su año es el
    día en que corrió ese script. Da 2026 y es correcto, pero por coincidencia
    de calendario: si esa siembra se hubiera hecho el 2025-12-30 —un plan de
    2026 cargado en diciembre, que es lo normal— habría dado 2025. Por eso las
    fuentes declaradas van primero.

  · **Es la vigencia de la FORMULACIÓN, no la del contrato que resulte.** En
    esta base son cosas distintas y está medido: el contrato 1001-2025 declara
    `contrato_vigencia = 2025` y se ejecuta del 2026-03-02 al 2026-12-01 —plata
    de 2025 corriendo en 2026—, y el 983-2025 va a caballo entre los dos años.
    De los 25 contratos, 23 son vigencia 2025 y NINGUNO es 2026. Así que es
    perfectamente posible que el contrato que termine financiando una de estas
    seis sea de vigencia 2025: eso no invalida la formulación de 2026, son dos
    años distintos de dos cosas distintas.
  · **El valor estimado queda NULL — y NO es por no haber mirado la fuente.**
    `sdp_meta_oficial` SÍ publica `valor_programado` por actividad oficial, y
    se revisó. No se copia por dos razones medidas:

      (a) **La tabla no publica una cifra anual que copiar.** Sus 70
          combinaciones proyecto×actividad están replicadas en 2025, 2026, 2027
          y 2028 con el MISMO `valor_programado` y la misma magnitud. La
          columna `vigencia` es un fan-out de la ingesta, no un hecho por año:
          no existe «el valor de 2026».
      (b) Aunque existiera, **no es el mismo número**. El `valor_programado` de
          SDP es lo que el plan destina a esa actividad completa y cubre todos
          sus contratos; el `valor_estimado` de una formulación es lo que vale
          UN proceso. Copiarlo diría que la formulación vale todo el plan.

    (Una corrección al pasar, porque estuvo escrito al revés: el emparejamiento
    con SDP **sí tiene llave guardada** —`metas.codigo_meta` =
    `sdp_meta_oficial.plan_meta_producto_id`— y resuelve 1:1 en las seis. Los
    «desajustes» de magnitud que se citaron como prueba de mal emparejamiento
    no lo eran: 280 contra 70 y 60 contra 15 son cuatrienio contra año, 4×.)

    Así que queda `Sin dato`, que es la verdad, y el valor lo pone el área.
  · **El responsable queda NULL.** Tampoco hay evidencia.
  · **Cero requisitos marcados.** El sistema no sabe si hay estudios previos ni
    CDP, así que la pantalla dirá «⚪ Sin iniciar · Todavía no se ha
    diligenciado ningún requisito», que es la verdad.

EL ESTADO ES «Borrador», y la primera versión se equivocó. Decía «En
elaboración» justificándolo en que «el área está ejecutando eventos contra
ellas», y eso es medible y FALSO para cuatro de las seis: `captura_generica`
tiene 0 filas, los eventos 69-72 no tienen ni un participante, uno se llama
«Actividad de prueba QA - jorge», y las 24 inscripciones del Banco están todas
en 'enviada' —el puntaje automático corrió, pero ninguna la validó un comité—.
Sólo la #113 tiene ejecución real: tres festivales celebrados.

Y hay un argumento más de fondo: **«no tiene contrato» es un JOIN de innovaK,
no un hecho del mundo.** Hay 25 contratos y sólo 15 vínculos vivos en
`contrato_actividad_plan`; para las cinco de Cultura, SDP reporta plata ya
comprometida y girada. La única con 0/0 en la fuente oficial es el Banco (#108),
que es justo el caso que Alex describió. Derivar una etapa de esa ausencia
sería el «0 que es un JOIN vacío» que este proyecto ya documentó dos veces.
"""
from django.core.management.base import BaseCommand

#: Las que se van a sembrar: con indicador activo y SIN contrato vivo.
#:
#: LA VIGENCIA SALE DE LA MEJOR FUENTE DISPONIBLE, EN ESTE ORDEN, y el comando
#: dice de cuál salió cada una. No es un lujo: si sale de un evento, el año
#: puede ser el día en que corrió un script de siembra (ver el docstring).
#:
#:   1. `festival.vigencia` — año DECLARADO. Es un dato, no una inferencia.
#:   2. `meta_proyecto.fecha_inicio` — la meta acota cuándo va la actividad.
#:   3. el evento VIVO más antiguo — el último recurso.
#:
#: `e.activo IS NOT FALSE` en todas las subconsultas de evento. Sin eso, un
#: evento soft-borrado fija una vigencia institucional: la actividad 109 tiene
#: uno («Actividad de prueba QA») y hay cuatro actividades cuyo ÚNICO evento
#: está inactivo. Hoy ésas no son candidatas porque tienen contrato, pero la
#: puente `contrato_actividad_plan` también se desactiva por soft delete.
SQL_CANDIDATAS = """
    SELECT ap.id, ap.descripcion, p.subgrupo_id,
           COALESCE(
             (SELECT min(f.vigencia)::int
                FROM evento e JOIN festival f ON f.id = e.festival_id
               WHERE e.actividad_plan_id = ap.id AND e.activo IS NOT FALSE
                 AND f.vigencia IS NOT NULL),
             (SELECT min(EXTRACT(YEAR FROM mp.fecha_inicio))::int
                FROM meta_proyecto mp
               WHERE mp.proyecto_id = ap.proyecto_id AND mp.fecha_inicio IS NOT NULL),
             (SELECT min(EXTRACT(YEAR FROM e.fecha_inicio))::int
                FROM evento e
               WHERE e.actividad_plan_id = ap.id AND e.activo IS NOT FALSE)
           ) AS vigencia,
           CASE
             WHEN EXISTS (SELECT 1 FROM evento e JOIN festival f ON f.id = e.festival_id
                           WHERE e.actividad_plan_id = ap.id AND e.activo IS NOT FALSE
                             AND f.vigencia IS NOT NULL) THEN 'festival.vigencia (declarada)'
             WHEN EXISTS (SELECT 1 FROM meta_proyecto mp
                           WHERE mp.proyecto_id = ap.proyecto_id
                             AND mp.fecha_inicio IS NOT NULL) THEN 'meta_proyecto.fecha_inicio'
             ELSE 'evento vivo más antiguo'
           END AS origen_vigencia,
           (SELECT count(*) FROM evento e
             WHERE e.actividad_plan_id = ap.id AND e.activo IS NOT FALSE) AS n_eventos
    FROM actividad_plan ap
    JOIN proyecto p ON p.id = ap.proyecto_id
    WHERE EXISTS (SELECT 1 FROM actividad_indicador ai
                  WHERE ai.actividad_plan_id = ap.id AND ai.activo)
      AND NOT EXISTS (SELECT 1 FROM contrato_actividad_plan cap
                      WHERE cap.actividad_plan_id = ap.id AND cap.activo)
    ORDER BY p.subgrupo_id, ap.id
"""

#: Nace en BORRADOR, igual que el alta por pantalla (`formulacion_views.py`).
#: La primera versión la ponía en «En elaboración» y era una afirmación que el
#: sistema no puede sostener: una fila con cero requisitos, valor NULL y
#: responsable NULL es exactamente lo que el catálogo define como Borrador
#: —«creada, todavía sin diligenciar»—, y la pantalla habría dicho «En
#: elaboración» junto a «⚪ Sin iniciar» al mismo tiempo. Peor: la fila hecha
#: por máquina declaraba MÁS avance que cualquiera que pueda crear una persona.
#: (1,2) es transición válida: el área la mueve cuando lo diga, y esa vez sí
#: queda con fecha y autor de verdad.
ESTADO_BORRADOR = 1


class Command(BaseCommand):
    help = ("Siembra como Formulación las actividades del plan con indicador y "
            "sin contrato (seco por defecto).")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe de verdad. Sin esto sólo reporta.")
        parser.add_argument("--usuario", default=None,
                            help="Username de quien corre la siembra. OBLIGATORIO "
                                 "con --write: la auditoría no puede quedar sin autor.")

    def handle(self, *args, **opciones):
        from django.db import connection, transaction
        from django.utils import timezone

        from apps.presupuesto.models import Formulacion
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.services.auditoria import registrar_cambio

        escribir = opciones["write"]

        # Sin autor no se siembra. `registrar_cambio` con `usuario=None` escribe
        # `usuario_id = 0` —comprobado— y el usuario 0 NO EXISTE: quedaría una
        # fila de auditoría atribuida a alguien inventado, en la tabla que
        # existe justamente para poder decir quién hizo qué.
        autor = None
        if escribir:
            from django.contrib.auth import get_user_model
            username = opciones["usuario"]
            if not username:
                self.stderr.write(self.style.ERROR(
                    "  Falta --usuario. Una siembra sobre la base de producción "
                    "no puede quedar sin autor en la auditoría."))
                return
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                self.stderr.write(self.style.ERROR(
                    f"  El usuario «{username}» no existe."))
                return
            self.stdout.write(f"  Firma: {autor.username} (id {autor.id})\n")

        with connection.cursor() as cur:
            cur.execute(SQL_CANDIDATAS)
            candidatas = cur.fetchall()

        creadas = existian = sin_vigencia = 0
        for act_id, descripcion, subgrupo_id, anio, origen, n_eventos in candidatas:
            etiqueta = (descripcion or "")[:58]
            if anio is None:
                sin_vigencia += 1
                self.stdout.write(self.style.WARNING(
                    f"  SE OMITE     #{act_id} «{etiqueta}» — no hay de dónde "
                    f"sacar la vigencia (sin festival, sin fechas de meta y sin "
                    f"eventos vivos). La dice el área."))
                continue
            if Formulacion.objects.filter(actividad_plan_id=act_id,
                                          vigencia_id=anio).exists():
                existian += 1
                self.stdout.write(f"  ya existía   #{act_id} «{etiqueta}» ({anio})")
                continue

            creadas += 1
            self.stdout.write(
                f"  {'CREARÍA' if not escribir else 'creada '}      #{act_id} "
                f"«{etiqueta}» · vigencia {anio} ← {origen} "
                f"· sub {subgrupo_id} · {n_eventos} evento(s) vivo(s)")
            if not escribir:
                continue

            ahora = timezone.now()
            with transaction.atomic():
                f = Formulacion.objects.create(
                    actividad_plan_id=act_id, vigencia_id=anio,
                    subgrupo_id=subgrupo_id,
                    objeto=descripcion,
                    # valor_estimado y responsable quedan NULL A PROPÓSITO: no
                    # hay dato, y un número plausible sería inventarlo.
                    estado_id=ESTADO_BORRADOR, estado_fecha=ahora,
                    # El autor va en las TRES columnas, no sólo en la auditoría.
                    # Dejarlas NULL mientras la auditoría nombra a alguien deja
                    # dos registros del mismo hecho en desacuerdo.
                    estado_usuario_id=autor.id if autor else None,
                    creado_en=ahora,
                    creado_usuario_id=autor.id if autor else None,
                    # De dónde salió el texto, para que dentro de un año se
                    # distinga lo que redactó el área de lo que copió un comando.
                    descripcion=("Objeto tomado del enunciado del plan al sembrar "
                                 "la formulación. El área debe redactar el objeto "
                                 "contractual."))
                registrar_cambio(
                    usuario=autor, entidad="formulacion", entidad_id=f.id,
                    campo="creacion", valor_anterior=None,
                    valor_nuevo=f"{(descripcion or '')[:60]} · vigencia {anio}",
                    # SISTEMA y no MANUAL: la fila la derivó un comando de una
                    # regla, no la escribió una persona campo por campo. Pero el
                    # autor sí es una persona, y por eso `--usuario` es obligatorio.
                    subgrupo_id=subgrupo_id, fuente=AuditoriaDato.SISTEMA,
                    observacion=("Sembrada desde `actividad_plan` por tener "
                                 "indicador y no tener contrato. Vigencia "
                                 f"{anio} tomada de: {origen}. Es la vigencia de "
                                 "la FORMULACIÓN, no necesariamente la del "
                                 "contrato que resulte."))

        self.stdout.write("")
        # El 0 se explica: un cero anónimo se lee como «no hubo problemas» y
        # acá significa «la guarda no tuvo que actuar», que es distinto.
        detalle_omitidas = (f"omitidas {sin_vigencia}" if sin_vigencia else
                            "omitidas 0 (ninguna candidata se quedó sin vigencia)")
        self.stdout.write(f"  candidatas {len(candidatas)} · nuevas {creadas} · "
                          f"ya existían {existian} · {detalle_omitidas}")
        if not escribir:
            self.stdout.write(self.style.WARNING(
                "  SECO: no se escribió nada. Corré con --write para aplicarlo."))
