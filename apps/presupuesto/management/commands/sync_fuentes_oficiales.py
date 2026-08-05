"""Orquestador: sincroniza las fuentes oficiales en un solo paso.

Cubre las 11 fuentes de docs/RUMBO.md §1.1 con 10 invocaciones (Colegios trae
sedes + matrícula en una corrida). Config declarativa: agregar una fuente es una
entrada en FUENTES, no código nuevo.

SECO POR DEFECTO. Sin `--write` no escribe nada: cada comando corre en su modo
de solo-lectura. Con `--write` persiste. Esto **invierte el default viejo**, que
era peligroso: el orquestador escribía SDP/SECOP sin flag, así que una corrida
de exploración terminaba tocando la BD. Ahora el que persiste es el cron (pasa
`--write`), no una corrida manual para ver qué traería.

Cada fuente declara cómo se comporta SIN flags (`modo`) y el orquestador traduce
eso al flag correcto de cada comando. Es un PUENTE hasta C3: cuando todos los
comandos sean secos-por-defecto (un solo `--write` en todo el repo), este mapeo
por convención desaparece y el orquestador pasará un único flag uniforme.

Uso:
    # seco (no escribe): muestra qué traería cada fuente
    docker exec innova_k python manage.py sync_fuentes_oficiales
    # escribe de verdad (lo que hace el cron)
    docker exec innova_k python manage.py sync_fuentes_oficiales --write --desde-anio 2024
    # incluir las pesadas (placas: 1,77M filas, horas) — NO en el cron diario
    docker exec innova_k python manage.py sync_fuentes_oficiales --write --incluir-pesadas
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


# (etiqueta, comando, args_posicionales, modo, pesado)
#
# `modo` describe qué hace el comando SIN flags:
#   'seco'         → seco por defecto; escribe con write=True     (sync_capa, sync_placas)
#   'escribe'      → escribe por defecto; seco con dry_run=True    (sync_cai, sync_colegios, ingest_*)
#   'solo_write'   → sin modo seco (siempre escribe); se SALTA en dry-run (resolver_geometria_tramos)
#   'solo_lectura' → nunca persiste; corre siempre                (sdp_preview)
# `pesado=True` se salta salvo --incluir-pesadas (placas = 1,77M filas / horas).
FUENTES = [
    ("Estratificación (IDECA)",         "sync_capa", ["estratificacion"],     "seco",         False),
    ("Sectores catastrales (IDECA)",    "sync_capa", ["sector_catastral"],    "seco",         False),
    ("Barrios legalizados (IDECA)",     "sync_capa", ["barrios_legalizados"], "seco",         False),
    ("Colegios + Matrícula (SED)",      "sync_colegios", [],                   "escribe",      False),
    ("CAI (SCJ)",                       "sync_cai", [],                        "escribe",      False),
    ("SDP-PDL (Planeación)",            "ingest_sdp_datos_abiertos", [],       "escribe",      False),
    ("SECOP II (contratos)",            "ingest_secop_contratos", [],          "escribe",      False),
    ("Malla vial (IDU)",                "resolver_geometria_tramos", [],       "solo_write",   False),
    ("Presupuesto PP (CKAN, preview)",  "sdp_preview", [],                     "solo_lectura", False),
    ("Placas domiciliarias (Catastro)", "sync_placas", [],                     "seco",         True),
]


def kwargs_por_modo(modo, write):
    """Traduce (modo del comando, ¿escribimos?) → (kwargs, ¿correr?).

    `correr=False` significa que la fuente se salta: es un comando sin modo seco
    (siempre escribe) y esta corrida NO lleva --write, así que no se toca.
    """
    if modo == "solo_lectura":
        return {}, True                                  # nunca persiste
    if modo == "solo_write":
        return ({}, True) if write else ({}, False)      # sin dry-run: se salta en seco
    if modo == "seco":
        return ({"write": True} if write else {}), True
    if modo == "escribe":
        return ({} if write else {"dry_run": True}), True
    return {}, True


class Command(BaseCommand):
    help = ("Sincroniza las 11 fuentes oficiales (RUMBO §1.1). Seco por defecto; "
            "--write para persistir. Idempotente (upsert por hash).")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true", default=False,
                            help="Escribe en la BD. Sin este flag no persiste nada (default seco).")
        parser.add_argument("--desde-anio", type=int, default=None,
                            help="Pasa --desde-anio a las ingestas que lo soportan (SECOP).")
        parser.add_argument("--incluir-pesadas", action="store_true", default=False,
                            help="Incluye fuentes pesadas (placas: 1,77M filas, horas). No usar en cron diario.")

    def handle(self, *args, **opts):
        write = opts["write"]
        incluir_pesadas = opts["incluir_pesadas"]
        desde_anio = opts.get("desde_anio")

        inicio = timezone.now()
        log = self._abrir_log(inicio)
        modo_txt = ("ESCRITURA (--write)" if write
                    else "SECO (no escribe; usa --write para persistir)")
        self._emit(log, self.style.MIGRATE_HEADING(
            f"=== SYNC FUENTES OFICIALES · {inicio:%Y-%m-%d %H:%M} · {modo_txt} ==="))

        resultados = []
        for etiqueta, cmd, pos, modo, pesado in FUENTES:
            if pesado and not incluir_pesadas:
                self._emit(log, f"\n⏭  {etiqueta}: SALTADA (pesada; corre con --incluir-pesadas)")
                resultados.append((etiqueta, "SALTADA (pesada)"))
                continue
            kwargs, correr = kwargs_por_modo(modo, write)
            if not correr:
                self._emit(log, f"\n⏭  {etiqueta}: SALTADA (solo escribe; corre con --write)")
                resultados.append((etiqueta, "SALTADA (solo --write)"))
                continue
            if desde_anio and cmd == "ingest_secop_contratos":
                kwargs = {**kwargs, "desde_anio": desde_anio}
            self._emit(log, f"\n▶ {etiqueta} …")
            try:
                call_command(cmd, *pos, **kwargs)
                resultados.append((etiqueta, "OK"))
            except Exception as e:  # noqa: BLE001 — una fuente no debe tumbar el resto
                self._emit(log, self.style.ERROR(f"  ✗ {etiqueta} falló: {e!r}"))
                resultados.append((etiqueta, f"FALLÓ: {e!r}"))

        dur = (timezone.now() - inicio).total_seconds()
        self._emit(log, self.style.MIGRATE_HEADING(f"\n=== RESUMEN ({dur:.0f}s) ==="))
        for etiqueta, estado in resultados:
            self._emit(log, f"  {etiqueta}: {estado}")
        if all(e == "OK" for _, e in resultados):
            self._emit(log, self.style.SUCCESS("Todas las fuentes sincronizadas."))
        elif not write:
            self._emit(log, self.style.WARNING(
                "Corrida SECA: nada se escribió. Repite con --write para persistir."))

        # Atribución obligatoria (CC BY 4.0): se declara en cada corrida.
        from core.licencias import bloque_atribucion
        self._emit(log, "\nAtribución de las fuentes (CC BY 4.0):")
        self._emit(log, bloque_atribucion())
        if log:
            log.close()

    # ── logging a archivo (para que las corridas manuales también queden) ──

    def _abrir_log(self, inicio):
        """Abre logs/sync_oficial_<fecha>.log en modo append. None si no se puede
        (el log nunca debe impedir la sincronización)."""
        try:
            logs_dir = Path(settings.BASE_DIR) / "logs"
            logs_dir.mkdir(exist_ok=True)
            return open(logs_dir / f"sync_oficial_{inicio:%Y-%m-%d}.log",
                        "a", encoding="utf-8")
        except Exception:  # noqa: BLE001
            return None

    def _emit(self, log, linea):
        """Escribe a stdout (con color) y al archivo (texto plano, sin ANSI)."""
        self.stdout.write(linea)
        if log:
            log.write(re.sub(r"\x1b\[[0-9;]*m", "", str(linea)) + "\n")
            log.flush()
