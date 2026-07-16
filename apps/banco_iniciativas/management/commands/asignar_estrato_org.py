"""Asigna el estrato oficial (IDECA) de la ORGANIZACIÓN.

Dos vías, de menor a mayor precisión:

1. **Por barrio declarado** (default, histórico): mayoría de las manzanas del
   barrio. Es una *aproximación* — un barrio puede tener manzanas de varios
   estratos. Límite duro: solo 75 de los 325 barrios tienen geometría (deuda M22).

2. **Por dirección** (`--por-direccion`, recomendado): geocodifica la dirección
   contra la capa oficial de placas domiciliarias de Catastro y resuelve el estrato
   de la manzana donde cae el punto. **Exacto, y no depende de M22.**

       dirección → placa domiciliaria oficial → punto → manzana → estrato

Medido sobre las 24 del piloto (evento 62, 2026-07-16): por barrio resuelve **6/24**;
por dirección **12/24**; la unión de ambas, **14/24**.

El geocoding además **delata** lo que la aproximación por barrio ocultaba: 5
organizaciones declararon un barrio de Kennedy pero dieron una dirección de otra
localidad. Salen como `fuera_kennedy` → revisión manual, no cálculo automático.

Sirve para **validación cruzada** contra `estrato` (lo que la organización declara).
**No alimenta el puntaje** (eso sería PR-7, y está sin decidir).

Uso:
    python manage.py asignar_estrato_org                          # dry-run, por barrio
    python manage.py asignar_estrato_org --por-direccion          # dry-run, geocoding
    python manage.py asignar_estrato_org --por-direccion --write  # persiste
    python manage.py asignar_estrato_org --por-direccion --evento 62
"""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from apps.banco_iniciativas.models import InscripcionBancoIniciativa
from apps.georeferenciacion.services.geo_estrato import estrato_de_barrio


class Command(BaseCommand):
    help = "Asigna estrato_ideca_org (por barrio declarado o por geocoding de la dirección)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Persiste estrato_ideca_org (default: dry-run).")
        parser.add_argument("--refrescar", action="store_true",
                            help="Ignora la caché y re-consulta Catastro. Necesario "
                                 "tras arreglar el parser: los negativos cacheados "
                                 "(sin_hit, fuera_kennedy) se calcularon con el "
                                 "parser viejo y no se recalculan solos.")
        parser.add_argument("--por-direccion", action="store_true",
                            help="Geocodifica la dirección contra Catastro (más preciso, "
                                 "no depende de M22). Cae a barrio si no resuelve.")
        parser.add_argument("--evento", type=int, default=None,
                            help="Limita a un evento (p. ej. 62, el piloto).")

    def handle(self, *args, **opts):
        qs = InscripcionBancoIniciativa.objects.all().only(
            "id", "barrio_id", "estrato", "estrato_ideca_org", "direccion", "evento_id")
        if opts["evento"]:
            qs = qs.filter(evento_id=opts["evento"])

        if opts["por_direccion"]:
            self._por_direccion(qs, opts)
        else:
            self._por_barrio(qs, opts)

    # ── Vía 1: barrio declarado (comportamiento histórico) ──────────────────

    def _por_barrio(self, qs, opts):
        cache_barrio: dict = {}
        resueltas = sin_barrio = sin_geometria = escritas = 0
        coincide = difiere = sin_comparar = 0
        total = 0

        for ins in qs.iterator():
            total += 1
            cod = ins.barrio_id
            if cod is None:
                sin_barrio += 1
                continue

            if cod not in cache_barrio:
                cache_barrio[cod] = estrato_de_barrio(cod)
            r = cache_barrio[cod]

            if r["estrato"] is None:
                sin_geometria += 1
            else:
                resueltas += 1
                if ins.estrato is None:
                    sin_comparar += 1
                elif ins.estrato == r["estrato"]:
                    coincide += 1
                else:
                    difiere += 1

            if opts["write"]:
                InscripcionBancoIniciativa.objects.filter(id=ins.id).update(
                    estrato_ideca_org=r["estrato"])
                escritas += 1

        self._encabezado(opts, total, escritas)
        self.stdout.write("Resolución por BARRIO declarado (aproximación):")
        self.stdout.write(f"  resueltas por barrio      {resueltas:>4}")
        self.stdout.write(f"  barrio sin geometría      {sin_geometria:>4}   ← deuda M22, quedan NULL")
        self.stdout.write(f"  sin barrio declarado      {sin_barrio:>4}")
        self._cruzada(resueltas, coincide, difiere, sin_comparar)

        if sin_geometria:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"{sin_geometria} inscripciones sin resolver: su barrio no tiene geometría "
                f"(M22). Cruzar nuestro catálogo de 325 barrios por nombre contra las capas "
                f"oficiales es un callejón sin salida (barrioslegalizados 2/13, "
                f"sectorcatastral 3/13). Usa --por-direccion: no depende de M22."))
        self._pie(opts)

    # ── Vía 2: geocoding de la dirección (recomendado) ──────────────────────

    #: Métodos donde el barrio declarado NO puede rescatar el estrato.
    #: `fuera_kennedy` no significa "no sabemos dónde está" sino "sabemos que
    #: no está aquí": la dirección resolvió, y resolvió fuera de la localidad.
    METODOS_SIN_RESCATE = frozenset({"fuera_kennedy"})

    @classmethod
    def _rescatable_por_barrio(cls, estrato, metodo, barrio_id) -> bool:
        """¿Se puede aproximar el estrato por el barrio que declaró la organización?

        Sí cuando simplemente no la ubicamos (no está en la capa, no se pudo
        parsear la dirección, no la declaró): el barrio es lo mejor que hay.

        No cuando la ubicamos y cayó fuera de Kennedy. Imputarle ahí el estrato
        del barrio de Kennedy que declaró sería afirmar lo contrario de la
        evidencia — y esto alimenta un puntaje que reparte recursos públicos.
        Queda en NULL: revisión manual, que es la respuesta honesta.
        """
        # `estrato` falsy cubre None y 0: el 0 de Catastro es "sin estrato
        # oficial" (parque, colegio, dotacional), o sea ausencia de dato, no
        # un estrato bajo. `geo_estrato` ya no lo devuelve; acá se blinda igual.
        if estrato or barrio_id is None:
            return False
        return metodo not in cls.METODOS_SIN_RESCATE

    def _por_direccion(self, qs, opts):
        from apps.georeferenciacion.services.geocoder import estrato_de_direccion

        metodos: Counter = Counter()
        cache_barrio: dict = {}
        total = escritas = con_estrato = 0
        por_barrio_rescate = 0
        coincide = difiere = sin_comparar = 0
        fuera = []

        for ins in qs.iterator():
            total += 1
            direccion = (ins.direccion or "").strip()
            estrato = None
            metodo = None

            if direccion:
                try:
                    r = estrato_de_direccion(direccion,
                                            refrescar=opts["refrescar"])
                except Exception as exc:            # red caída → no rompe el lote
                    metodos["error_red"] += 1
                    self.stderr.write(self.style.WARNING(f"  id={ins.id}: {exc}"))
                    r = None
                if r:
                    metodo = r["metodo"]
                    metodos[metodo] += 1
                    estrato = r["estrato"]
                    if metodo == "fuera_kennedy":
                        fuera.append((ins.id, direccion[:44], ins.barrio_id))
            else:
                metodo = "sin_direccion"
                metodos[metodo] += 1

            # Se persiste ANTES del rescate: `fuera_kennedy` describe lo que dijo
            # la dirección, y eso no lo cambia que después aproximemos por barrio.
            fuera_de_kennedy = metodo == "fuera_kennedy"

            if self._rescatable_por_barrio(estrato, metodo, ins.barrio_id):
                if ins.barrio_id not in cache_barrio:
                    cache_barrio[ins.barrio_id] = estrato_de_barrio(ins.barrio_id)
                b = cache_barrio[ins.barrio_id]
                if b["estrato"] is not None:
                    estrato = b["estrato"]
                    metodo = "barrio"          # el estrato ya no viene de la dirección
                    por_barrio_rescate += 1

            if estrato is not None:
                con_estrato += 1
                if ins.estrato is None:
                    sin_comparar += 1
                elif ins.estrato == estrato:
                    coincide += 1
                else:
                    difiere += 1

            if opts["write"]:
                InscripcionBancoIniciativa.objects.filter(id=ins.id).update(
                    estrato_ideca_org=estrato,
                    fuera_kennedy=fuera_de_kennedy,
                    geo_metodo=metodo)
                escritas += 1

        self._encabezado(opts, total, escritas)
        self.stdout.write("Resolución por DIRECCIÓN (geocoding contra Catastro):")
        for m, n in metodos.most_common():
            nota = {
                "placa_exacta": "← la dirección existe en la capa oficial",
                "via_mayoria": "← la placa no existe; mayoría de la vía",
                "fuera_kennedy": "← resolvió FUERA de la localidad: revisión manual",
                "sin_hit": "← no está en la capa (¿error de digitación?)",
                "no_parseable": "← no se reconoce vía + placa",
                "sin_direccion": "← la inscripción no declaró dirección",
                "error_red": "← falló la consulta a Catastro",
            }.get(m, "")
            self.stdout.write(f"  {m:<16} {n:>4}   {nota}")
        if por_barrio_rescate:
            self.stdout.write(f"  {'(rescate barrio)':<16} {por_barrio_rescate:>4}   "
                              f"← no resolvió por dirección; se usó el barrio")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"CON ESTRATO: {con_estrato} de {total}"))
        self._cruzada(con_estrato, coincide, difiere, sin_comparar)

        if fuera:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Declararon barrio de Kennedy pero la dirección cae FUERA de la localidad:"))
            for iid, d, bid in fuera:
                self.stdout.write(f"    id={iid:<5} barrio={bid!s:<6} {d!r}")
            self.stdout.write(self.style.WARNING(
                "  Aproximar por barrio les habría asignado el estrato del barrio declarado "
                "sin avisar. Quedan en NULL a propósito: son revisión manual."))
        self._pie(opts)

    # ── Salida común ────────────────────────────────────────────────────────

    def _encabezado(self, opts, total, escritas):
        modo = (self.style.SUCCESS("ESCRITO") if opts["write"]
                else self.style.WARNING("DRY-RUN (no se escribió)"))
        self.stdout.write("")
        self.stdout.write(f"{modo}: {total} inscripciones"
                          + (f" | filas actualizadas {escritas}" if opts["write"] else ""))
        self.stdout.write("")

    def _cruzada(self, resueltas, coincide, difiere, sin_comparar):
        if not resueltas:
            return
        self.stdout.write("")
        self.stdout.write("Validación cruzada (lo declarado vs lo oficial):")
        self.stdout.write(f"  coinciden                 {coincide:>4}")
        self.stdout.write(f"  difieren                  {difiere:>4}")
        self.stdout.write(f"  sin estrato declarado     {sin_comparar:>4}")

    def _pie(self, opts):
        if not opts["write"]:
            self.stdout.write("")
            self.stdout.write("Para persistir: --write")
