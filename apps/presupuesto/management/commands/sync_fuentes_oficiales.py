"""Orquestador: sincroniza TODAS las fuentes oficiales en un solo paso.

Corre las ingestas idempotentes (SDP-PDL + SECOP II) en orden y reporta.
Pensado para un cron diario (ver scripts/cron_sync_oficial.sh). Como cada
ingesta hace upsert por hash, correr a diario solo trae lo nuevo/cambiado —
nada se duplica. Si una fuente falla, sigue con las demás y reporta al final.

Uso:
    docker exec innova_k python manage.py sync_fuentes_oficiales
    docker exec innova_k python manage.py sync_fuentes_oficiales --desde-anio 2024
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


FUENTES = [
    # (etiqueta, comando, kwargs)
    ("SDP-PDL (Planeación)", "ingest_sdp_datos_abiertos", {}),
    ("SECOP II (contratos)", "ingest_secop_contratos", {}),
]


class Command(BaseCommand):
    help = "Sincroniza todas las fuentes oficiales (SDP-PDL + SECOP II). Idempotente."

    def add_arguments(self, parser):
        parser.add_argument("--desde-anio", type=int, default=None,
                            help="Pasa --desde-anio a las ingestas que lo soportan (SECOP).")

    def handle(self, *args, **opts):
        inicio = timezone.now()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== SYNC FUENTES OFICIALES · {inicio:%Y-%m-%d %H:%M} ==="))
        resultados = []
        for etiqueta, cmd, kwargs in FUENTES:
            if opts.get("desde_anio") and cmd == "ingest_secop_contratos":
                kwargs = {**kwargs, "desde_anio": opts["desde_anio"]}
            self.stdout.write(f"\n▶ {etiqueta} …")
            try:
                call_command(cmd, **kwargs)
                resultados.append((etiqueta, "OK"))
            except Exception as e:  # noqa: BLE001 — una fuente no debe tumbar el resto
                self.stderr.write(self.style.ERROR(f"  ✗ {etiqueta} falló: {e!r}"))
                resultados.append((etiqueta, f"FALLÓ: {e!r}"))

        dur = (timezone.now() - inicio).total_seconds()
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== RESUMEN ({dur:.0f}s) ==="))
        for etiqueta, estado in resultados:
            self.stdout.write(f"  {etiqueta}: {estado}")
        if all(e == "OK" for _, e in resultados):
            self.stdout.write(self.style.SUCCESS("Todas las fuentes sincronizadas."))
