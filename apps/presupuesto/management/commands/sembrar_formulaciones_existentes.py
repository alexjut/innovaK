"""Siembra como Formulación lo que el área YA está formulando en el plan.

    docker exec innova_k python manage.py sembrar_formulaciones_existentes            # seco
    docker exec innova_k python manage.py sembrar_formulaciones_existentes --write

SECO POR DEFECTO e IDEMPOTENTE: la segunda corrida no duplica ni pisa nada.

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

  · **La vigencia sale de los eventos**, no de un criterio. Las seis tienen
    eventos entre 2026-05-04 y 2026-08-02, así que 2026. Si una actividad no
    tuviera eventos, NO se siembra: se reporta y se deja para que el área diga
    de qué año es.
  · **El valor estimado queda NULL — y NO es por no haber mirado la fuente.**
    `sdp_meta_oficial` SÍ publica `valor_programado` por actividad oficial, y
    se revisó. No se copia por dos razones medidas:

      (a) El emparejamiento sería POR PARECIDO DE TEXTO. De las seis, tres
          coinciden en magnitud con su actividad oficial (1.000 personas, 15
          organizaciones, 35 proyectos) y **tres NO**: estímulos 38 contra 35,
          eventos 60 contra 15, y el Banco 280 colectivos contra 70. Fundar
          plata pública en una coincidencia de nombres es justo el método que
          el diagnóstico ya marcó como no verificado en
          `sdp_mapear_codigo_meta.py`.
      (b) Aunque empatara, **no es el mismo número**. El `valor_programado` de
          SDP es lo que el plan destina a esa actividad EN EL AÑO, y cubre
          todos sus contratos; el `valor_estimado` de una formulación es lo que
          vale UN proceso. Copiarlo diría que la formulación vale todo el año.

    Así que queda `Sin dato`, que es la verdad, y el valor lo pone el área.
  · **El responsable queda NULL.** Tampoco hay evidencia.
  · **Cero requisitos marcados.** El sistema no sabe si hay estudios previos ni
    CDP, así que la pantalla dirá «⚪ Sin iniciar · Todavía no se ha
    diligenciado ningún requisito», que es la verdad.

EL ESTADO ES «En elaboración» y no «Borrador». Borrador significa «creada y sin
tocar», y sería falso: el área escribió estas líneas, les puso indicador y está
ejecutando eventos contra ellas. «En elaboración» es lo que de verdad pasa.
"""
from django.core.management.base import BaseCommand

#: Las que se van a sembrar: con indicador activo y SIN contrato vivo.
SQL_CANDIDATAS = """
    SELECT ap.id, ap.descripcion, p.subgrupo_id,
           (SELECT min(EXTRACT(YEAR FROM e.fecha_inicio))::int
              FROM evento e WHERE e.actividad_plan_id = ap.id),
           (SELECT count(*) FROM evento e WHERE e.actividad_plan_id = ap.id)
    FROM actividad_plan ap
    JOIN proyecto p ON p.id = ap.proyecto_id
    WHERE EXISTS (SELECT 1 FROM actividad_indicador ai
                  WHERE ai.actividad_plan_id = ap.id AND ai.activo)
      AND NOT EXISTS (SELECT 1 FROM contrato_actividad_plan cap
                      WHERE cap.actividad_plan_id = ap.id AND cap.activo)
    ORDER BY p.subgrupo_id, ap.id
"""

ESTADO_EN_ELABORACION = 2


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
        for act_id, descripcion, subgrupo_id, anio, n_eventos in candidatas:
            etiqueta = (descripcion or "")[:58]
            if anio is None:
                sin_vigencia += 1
                self.stdout.write(self.style.WARNING(
                    f"  SE OMITE     #{act_id} «{etiqueta}» — sin eventos, no hay "
                    f"de dónde sacar la vigencia. La dice el área."))
                continue
            if Formulacion.objects.filter(actividad_plan_id=act_id,
                                          vigencia_id=anio).exists():
                existian += 1
                self.stdout.write(f"  ya existía   #{act_id} «{etiqueta}» ({anio})")
                continue

            creadas += 1
            self.stdout.write(
                f"  {'CREARÍA' if not escribir else 'creada '}      #{act_id} "
                f"«{etiqueta}» · vigencia {anio} · sub {subgrupo_id} "
                f"· {n_eventos} evento(s)")
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
                    estado_id=ESTADO_EN_ELABORACION, estado_fecha=ahora,
                    creado_en=ahora)
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
                                 f"derivada de sus {n_eventos} evento(s)."))

        self.stdout.write("")
        self.stdout.write(f"  candidatas {len(candidatas)} · nuevas {creadas} · "
                          f"ya existían {existian} · omitidas {sin_vigencia}")
        if not escribir:
            self.stdout.write(self.style.WARNING(
                "  SECO: no se escribió nada. Corré con --write para aplicarlo."))
