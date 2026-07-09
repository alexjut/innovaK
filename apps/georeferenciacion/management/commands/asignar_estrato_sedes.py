"""Asigna el estrato oficial (IDECA) a cada sede/escuela.

Lee las coordenadas de `escuela` (solo lectura) y resuelve el estrato con
`geo_estrato.resolver_estrato()`. Por defecto es DRY-RUN: reporta lo que
asignaría sin escribir nada.

Las manzanas catastrales NO cubren vías, andenes ni parques. Con
point-in-polygon estricto, 62 de las 241 sedes quedaban sin estrato — y estaban
a una **mediana de 4 metros** de una manzana. Por eso el comando degrada en tres
pasos y **reporta con qué método resolvió cada sede** (`contenido`, `cercano`,
`entorno`), porque este dato alimenta un puntaje y debe ser auditable.

Uso:
    python manage.py asignar_estrato_sedes                    # dry-run, todas
    python manage.py asignar_estrato_sedes --solo 12,34       # solo esas
    python manage.py asignar_estrato_sedes --write            # persiste
    python manage.py asignar_estrato_sedes --estricto         # PIP puro (sin tolerancia)
    python manage.py asignar_estrato_sedes --tolerancia 50 --radio-entorno 200
"""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from apps.georeferenciacion.models import Escuela
from apps.georeferenciacion.services.geo_estrato import (
    RADIO_ENTORNO_M_DEFAULT,
    TOLERANCIA_M_DEFAULT,
    resolver_estrato,
)


class Command(BaseCommand):
    help = "Calcula/asigna el estrato oficial (IDECA) a las sedes."

    def add_arguments(self, parser):
        parser.add_argument("--solo", default="", help="IDs de escuela separados por coma.")
        parser.add_argument("--write", action="store_true",
                            help="Persiste estrato_ideca (default: dry-run, no escribe).")
        parser.add_argument("--backend", default=None, choices=["shapely", "postgis"])
        parser.add_argument("--tolerancia", type=float, default=TOLERANCIA_M_DEFAULT,
                            help="Metros para aceptar la manzana contigua (andén/vía).")
        parser.add_argument("--radio-entorno", type=float, default=RADIO_ENTORNO_M_DEFAULT,
                            help="Metros para el voto mayoritario del entorno (parques).")
        parser.add_argument("--estricto", action="store_true",
                            help="Point-in-polygon puro: tolerancia=0 y entorno=0.")
        parser.add_argument("--verbose-sedes", action="store_true",
                            help="Imprime una línea por sede (default: solo el resumen).")

    def handle(self, *args, **opts):
        tolerancia = 0.0 if opts["estricto"] else opts["tolerancia"]
        radio = 0.0 if opts["estricto"] else opts["radio_entorno"]

        qs = Escuela.objects.exclude(latitud__isnull=True).exclude(longitud__isnull=True)
        if opts["solo"]:
            ids = [int(x) for x in opts["solo"].split(",") if x.strip().isdigit()]
            qs = qs.filter(id__in=ids)

        self.stdout.write(
            f"Modo: {'ESTRICTO (PIP puro)' if opts['estricto'] else f'tolerancia={tolerancia:g} m · entorno={radio:g} m'}"
        )

        metodos = Counter()
        dist_estrato = Counter()
        total = escritas = 0
        detalle_snap = []

        for e in qs.iterator():
            r = resolver_estrato(float(e.longitud), float(e.latitud),
                                 tolerancia_m=tolerancia, radio_entorno_m=radio,
                                 backend=opts["backend"])
            total += 1
            metodos[r["metodo"] or "sin_resolver"] += 1
            dist_estrato[r["estrato"]] += 1

            if r["metodo"] in ("cercano", "entorno"):
                detalle_snap.append((e.nombre, r))

            if opts["verbose_sedes"] or opts["solo"]:
                marca = "→ escrito" if opts["write"] else "→ escribiría"
                extra = ""
                if r["metodo"] == "cercano":
                    extra = f"  [snap {r['distancia_m']} m]"
                elif r["metodo"] == "entorno":
                    extra = f"  [entorno: {r['n_entorno']} manzanas]"
                self.stdout.write(
                    f"[{e.id}] {e.nombre[:42]:42} estrato={r['estrato']}"
                    f" ({r['metodo']}){extra}  {marca}"
                )

            if opts["write"]:
                Escuela.objects.filter(id=e.id).update(estrato_ideca=r["estrato"])
                escritas += 1

        # ── resumen ──────────────────────────────────────────────────────────
        self.stdout.write("")
        modo = (self.style.SUCCESS("ESCRITO") if opts["write"]
                else self.style.WARNING("DRY-RUN (no se escribió)"))
        self.stdout.write(f"{modo}: {total} sedes"
                          + (f" | filas actualizadas {escritas}" if opts["write"] else ""))

        self.stdout.write("")
        self.stdout.write("Cómo se resolvió cada sede:")
        for m in ("contenido", "cercano", "entorno", "sin_resolver"):
            if metodos.get(m):
                self.stdout.write(f"  {m:14} {metodos[m]:>4}")

        self.stdout.write("")
        self.stdout.write("Distribución por estrato:")
        for est in sorted(dist_estrato, key=lambda x: (x is None, x)):
            etiqueta = "NULL (sin resolver)" if est is None else (
                "0 (sin estrato oficial)" if est == 0 else str(est))
            self.stdout.write(f"  estrato {etiqueta:24} {dist_estrato[est]:>4}")

        if detalle_snap and not opts["verbose_sedes"]:
            self.stdout.write("")
            self.stdout.write(f"{len(detalle_snap)} sedes resueltas por proximidad/entorno "
                              f"(usa --verbose-sedes para verlas todas). Muestra:")
            for nombre, r in detalle_snap[:8]:
                if r["metodo"] == "cercano":
                    self.stdout.write(f"  {nombre[:38]:38} estrato {r['estrato']}  "
                                      f"a {r['distancia_m']} m")
                else:
                    self.stdout.write(f"  {nombre[:38]:38} estrato {r['estrato']}  "
                                      f"entorno de {r['n_entorno']} manzanas")

        if not opts["write"]:
            self.stdout.write("")
            self.stdout.write("Para persistir: --write")
