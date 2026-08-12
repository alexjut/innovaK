"""Recalcula el Banco con la MATRIZ OFICIAL (Documento Maestro 2026-07-29).

SECO POR DEFECTO: sin `--write` no toca la base, solo muestra qué haría. Esa es
la convención de los comandos nuevos del proyecto y acá pesa el doble, porque
recalcular **sobreescribe** las evaluaciones del motor anterior y con ellas el
orden en que se reparte plata pública.

    # ver qué pasaría con el evento del piloto
    docker exec innova_k python manage.py recalcular_matriz_oficial --evento 62

    # aplicarlo de verdad
    docker exec innova_k python manage.py recalcular_matriz_oficial --evento 62 --write
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.banco_iniciativas.models import (
    BancoEvaluacionInscripcion,
    InscripcionBancoIniciativa,
)
from apps.banco_iniciativas.services.matriz_oficial import (
    CUPOS_ADJUDICABLES,
    DECISIONES_DEPORTES,
    MATRIZ_VERSION,
    TOTAL_MAX,
)
from apps.banco_iniciativas.services.ranking_oficial import (
    adjudicada,
    detalle_oficial,
    es_oficial,
    recalcular_lote_oficial,
)


class _Rollback(Exception):
    """Corta la transacción del ensayo sin dejar rastro."""


class Command(BaseCommand):
    help = ("Recalcula las inscripciones del Banco con la matriz oficial de 100 "
            "puntos y renumera el ranking. Seco por defecto: use --write.")

    def add_arguments(self, parser):
        parser.add_argument("--evento", type=int, required=True,
                            help="ID del evento del Banco a recalcular.")
        parser.add_argument("--write", action="store_true",
                            help="Persiste. Sin esto solo se muestra el resultado.")
        parser.add_argument("--top", type=int, default=10,
                            help="Cuántas filas del ranking mostrar (0 = todas).")

    def handle(self, *args, **opts):
        evento_id = opts["evento"]
        escribir = opts["write"]

        n = InscripcionBancoIniciativa.objects.filter(evento_id=evento_id).count()
        if not n:
            raise CommandError(f"El evento {evento_id} no tiene inscripciones.")

        previas = BancoEvaluacionInscripcion.objects.filter(
            inscripcion__evento_id=evento_id)
        a_sobreescribir = [e for e in previas if not es_oficial(e)]
        if a_sobreescribir:
            versiones = sorted({e.rubrica_version for e in a_sobreescribir})
            self.stdout.write(self.style.WARNING(
                f"⚠  {len(a_sobreescribir)} evaluaciones del motor anterior "
                f"({', '.join(versiones)}) van a quedar SOBREESCRITAS. La rúbrica "
                f"vieja se conserva en banco_rubrica, pero sus puntajes por "
                f"inscripción no: son irrecuperables sin restaurar un backup."))

        self.stdout.write(
            f"\n=== MATRIZ OFICIAL {MATRIZ_VERSION} · evento {evento_id} · "
            f"{'ESCRITURA (--write)' if escribir else 'ENSAYO (seco)'} ===\n")

        try:
            with transaction.atomic():
                res = recalcular_lote_oficial(evento_id)
                self._informe(evento_id, res, opts["top"])
                if not escribir:
                    raise _Rollback
        except _Rollback:
            self.stdout.write(self.style.WARNING(
                "\nENSAYO: nada se escribió. Repita con --write para aplicarlo."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\nEscrito: {res['procesadas']} evaluaciones y "
            f"{res['rankeadas']} posiciones de ranking."))

    def _informe(self, evento_id, res, top):
        evs = list(BancoEvaluacionInscripcion.objects
                   .filter(inscripcion__evento_id=evento_id,
                           rubrica_version=MATRIZ_VERSION)
                   .select_related("inscripcion", "inscripcion__organizacion")
                   .order_by("ranking_pos"))
        total = len(evs)

        filas = evs if top == 0 else evs[:top]
        self.stdout.write(f"{'pos':>4} {'total':>7} {'B1':>6} {'B2':>6}  "
                          f"{'tope':>12}  {'adj':>3}  organización")
        for ev in filas:
            d = detalle_oficial(ev)
            org = getattr(ev.inscripcion.organizacion, "nombre", "—") or "—"
            marca = "" if not d.get("formulario_anterior") else "  ← form. anterior"
            self.stdout.write(
                f"{ev.ranking_pos:>4} {float(ev.total or 0):>7.2f} "
                f"{(d.get('bloque1') or {}).get('pts', 0):>6.1f} "
                f"{(d.get('bloque2') or {}).get('pts', 0):>6.1f}  "
                f"{d.get('tope_presupuestal', 0):>12,}  "
                f"{'sí' if adjudicada(ev, total) else 'no':>3}  {org[:40]}{marca}")
        if top and total > top:
            self.stdout.write(f"     … y {total - top} más")

        anteriores = res.get("formulario_anterior", 0)
        self.stdout.write(
            f"\nPostuladas {total} · cupos {CUPOS_ADJUDICABLES} · "
            f"adjudicables {res.get('adjudicables')} · escala 0–{TOTAL_MAX:.0f}")
        if anteriores:
            self.stdout.write(self.style.WARNING(
                f"{anteriores} de {total} se diligenciaron con el FORMULARIO "
                f"ANTERIOR: no traen ningún campo de la sección 7, así que los "
                f"70 puntos del Bloque 2 les quedan inalcanzables y su techo "
                f"real es 30, no 100. Su puntaje NO es comparable con el de una "
                f"postulación nueva."))
        if res.get("cupos_insuficientes"):
            self.stdout.write(self.style.WARNING(
                f"Llegaron menos de {CUPOS_ADJUDICABLES}: aplica la política "
                f"'{res.get('politica_cupos_insuficientes')}' "
                f"(decisión 3, pendiente de Deportes)."))

        self.stdout.write("\nSupuestos provisionales que están corriendo hoy:")
        for clave, d in DECISIONES_DEPORTES.items():
            self.stdout.write(f"  · {clave}: {d['valor_hoy']}  "
                              f"(constante {d['constante']})")
