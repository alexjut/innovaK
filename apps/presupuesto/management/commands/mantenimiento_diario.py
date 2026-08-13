"""Deja al día lo que hoy depende de que alguien se acuerde de correrlo.

## Por qué existe

Cada pieza que construimos quedó actualizándose **en el momento en que alguien
la usa**: el avance se recalcula al procesar un cargue, el catálogo de
instituciones crece al pulsar un botón, los borradores se purgan cuando alguien
corre el comando. Funciona mientras haya alguien pendiente — y eso no es un
sistema, es una muleta.

Lo que este comando hace es simple: pasar por todo lo que debería estar al día
y ponerlo al día. Va al cron una vez al día y nadie tiene que acordarse.

## Tareas

    1. Recalcular el avance de los KPI de becas, por cada vigencia con datos.
    2. Sincronizar el catálogo de instituciones desde los beneficiarios.
    3. Purgar los borradores del Banco vencidos (habeas data: llevan cédulas).

Cada una es **idempotente**: correrla diez veces da lo mismo que una. Eso es lo
que permite programarla sin miedo — si un día no corre, el siguiente se pone al
día solo, sin acumular ni duplicar.

## Seco por defecto

Sin `--aplicar` solo informa qué haría. Un trabajo programado que escribe debe
poder ensayarse antes de programarlo, y sobre todo debe poder leerse su salida
sin tener que adivinar qué tocó.

## Qué NO hace, y por qué

**No geolocaliza instituciones nuevas.** Eso consulta un servicio externo y
propone coordenadas aproximadas que una persona tiene que revisar; meterlo en un
trabajo diario haría que aparecieran puntos en el mapa que nadie miró. Se corre
a mano cuando llega un lote nuevo (`geolocalizar_instituciones`).

**No toca datos del área.** No marca cumplimientos, no crea eventos, no cierra
vigencias. Solo recalcula lo que ya es derivable de lo que hay.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = ("Pone al día avances, catálogo de instituciones y purga de borradores. "
            "Seco por defecto: exige --aplicar.")

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true",
                            help="Ejecuta de verdad. Sin esto solo informa.")
        parser.add_argument("--solo", type=str, default="",
                            help="Corre una sola tarea: avances | instituciones | borradores.")

    def handle(self, *args, **opts):
        aplicar = opts["aplicar"]
        solo = (opts["solo"] or "").strip().lower()
        inicio = timezone.now()

        self.stdout.write(
            f"Mantenimiento diario · {inicio:%Y-%m-%d %H:%M} · "
            f"{'APLICANDO' if aplicar else 'SECO (no escribe)'}\n")

        tareas = [
            ("avances", self._avances),
            ("instituciones", self._instituciones),
            ("borradores", self._borradores),
        ]
        problemas = 0
        for nombre, tarea in tareas:
            if solo and solo != nombre:
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n▸ {nombre}"))
            try:
                tarea(aplicar)
            except Exception as exc:  # noqa: BLE001
                # Una tarea que falla NO puede tumbar a las demás: si el catálogo
                # de instituciones revienta, el avance de los KPI igual tiene que
                # quedar al día. El cron reporta y sigue.
                problemas += 1
                self.stdout.write(self.style.ERROR(
                    f"  falló: {exc.__class__.__name__}: {exc}"))

        dur = (timezone.now() - inicio).total_seconds()
        cierre = f"\nTerminado en {dur:.1f}s"
        if problemas:
            self.stdout.write(self.style.ERROR(f"{cierre} · {problemas} tarea(s) con error"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{cierre} · sin errores"))

    # ── Tareas ──────────────────────────────────────────────────────────

    def _avances(self, aplicar):
        """Recalcula el avance de los KPI de becas por vigencia.

        Recalcula, no acumula: el resultado es siempre lo que dicen los datos,
        así que da igual cuántas veces corra o si un día no corrió.
        """
        from apps.jovenes_a_la_e.models import EntregaBeca
        from apps.jovenes_a_la_e.services import avance as avance_becas
        from apps.login.models import Evento

        eventos = (Evento.objects.filter(tipo_evento_id="JOVENES_BECA")
                   .exclude(actividad_plan_id__isnull=True))
        if not eventos:
            self.stdout.write("  no hay eventos de becas atados al plan; nada que recalcular")
            return

        vigencias = sorted(set(EntregaBeca.objects.order_by()
                               .exclude(vigencia__isnull=True)
                               .values_list("vigencia", flat=True)))
        if not vigencias:
            self.stdout.write("  no hay entregas con vigencia; nada que recalcular")
            return

        for ev in eventos:
            for vig in vigencias:
                if not aplicar:
                    self.stdout.write(f"  [seco] recalcularía vigencia {vig} "
                                      f"(actividad {ev.actividad_plan_id})")
                    continue
                r = avance_becas.recalcular(vig, actividad_plan_id=ev.actividad_plan_id)
                for i in r["indicadores"]:
                    self.stdout.write(
                        f"  vigencia {vig} · KPI {i['indicador_id']} "
                        f"{i['nombre'][:38]:<38} {i['personas']:>5} personas ({i['accion']})")
                if r["motivo"]:
                    self.stdout.write(self.style.WARNING(f"    {r['motivo']}"))

    def _instituciones(self, aplicar):
        """Da de alta las instituciones y programas que aparezcan en los cargues."""
        from apps.educacion.services import instituciones as svc

        r = svc.sincronizar_desde_entregas(aplicar=aplicar)
        self.stdout.write(f"  instituciones nuevas: {r['instituciones_nuevas']} · "
                          f"programas nuevos: {r['programas_nuevos']}")
        for a in r["avisos"]:
            self.stdout.write(self.style.WARNING(f"  aviso: {a}"))

    def _borradores(self, aplicar):
        """Purga los borradores del Banco vencidos.

        Llevan cédulas de gente que ni siquiera llegó a radicar: la purga es una
        obligación de habeas data, no una limpieza de disco. Estaba escrita
        desde el 2026-08-12 y nadie la llamaba.
        """
        from django.core.management import call_command
        # El comando de purga usa `--write`, no `--aplicar`: cada uno nació con
        # su convención y traducirla acá es más honesto que renombrar la de él.
        opciones = {"write": True} if aplicar else {}
        call_command("purgar_borradores_banco", **opciones, stdout=self.stdout)
