"""Resuelve barrio y UPZ de cada escuela por geometría, y marca la discrepancia.

Consume `services/resolver_territorio.py` (ray casting en Python puro sobre el
JSONB; PostGIS no está disponible en el servidor y no se va a insistir).

## Qué escribe y qué NO

Escribe SOLO las columnas de resolución territorial que agregó el script
`014_escuela_censo_julio.sql`:

    barrio_resuelto   código del barrio contra cuyo polígono cayó el punto
    barrio_estado     resuelto | cercano_80m | sin_poligono | sin_coordenada
    upz_resuelta      código de UPZ (SIEMPRE, si hay coordenada)
    discrepancia      True cuando lo declarado no es lo que dice la geometría

**No toca** `barrio_declarado`, `barrio_codigo`, `upz_codigo`, `latitud`,
`longitud`, `nombre`, `direccion` ni nada del censo. La carga del censo es de
otro proceso; este comando resuelve territorio sobre lo que haya y se puede
correr después, tantas veces como haga falta (es idempotente).

Pisar el declarado con el resuelto borraría justo la evidencia que se quiere
auditar: la misma dirección reportada como "Pio XXII" y como "Urbanización
Catania" tiene que poder verse como discrepancia, no desaparecer.

## De dónde sale el "declarado"

De `barrio_declarado` si está poblado. Si viene NULL —porque el censo aún no se
cargó— se cae al nombre del barrio al que apunta `barrio_codigo`, que es el
declarado de la carga anterior. En ninguno de los dos casos se ESCRIBE el
declarado: solo se lee para comparar.

## Uso

    docker exec innova_k python manage.py resolver_territorio_escuelas            # dry-run
    docker exec innova_k python manage.py resolver_territorio_escuelas --apply
    docker exec innova_k python manage.py resolver_territorio_escuelas --reporte /tmp/r.csv
"""
from __future__ import annotations

import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.georeferenciacion.services import resolver_territorio as rt
from apps.georeferenciacion.services.diagnostico import (
    NO_INTENTADO, OK, SIN_HIT, Diagnostico,
)


class Command(BaseCommand):
    help = ("Resuelve barrio/UPZ de las escuelas por point-in-polygon sobre el "
            "JSONB y marca la discrepancia contra el barrio declarado.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Escribe en BD. Sin esta flag corre dry-run.")
        parser.add_argument("--tolerancia-m", type=float,
                            default=rt.TOLERANCIA_BORDE_M,
                            help=f"Metros del borde que aún cuentan como el barrio "
                                 f"(default {rt.TOLERANCIA_BORDE_M:.0f}; es el que "
                                 f"nombra el literal cercano_80m).")
        parser.add_argument("--reporte", default=None,
                            help="CSV con el detalle por escuela (útil para revisar "
                                 "las discrepancias a mano).")

    def handle(self, *args, **opts):
        aplicar = bool(opts["apply"])
        tolerancia = float(opts["tolerancia_m"])

        self._verificar_columnas()

        diag = Diagnostico()
        barrios = rt.cargar_barrios_bd(diag=diag)
        upzs = rt.cargar_upz_bd(diag=diag)
        self.stdout.write(self.style.NOTICE(
            f"polígonos cargados — barrios: {len(barrios)} | UPZ: {len(upzs)}"))
        if not upzs:
            raise CommandError(
                "Ninguna UPZ con geometría. Sin eso no se puede garantizar la regla "
                "de que todo registro con coordenada quede ubicado.")
        if not barrios:
            self.stdout.write(self.style.WARNING(
                "Ningún barrio con geometría: todo quedará en 'sin_poligono'. "
                "Corre antes `manage.py recuperar_barrios_ideca --apply`."))

        escuelas = self._escuelas()
        self.stdout.write(self.style.NOTICE(f"escuelas: {len(escuelas)}"))

        # El mismo vocabulario que usa `resolver_punto` para decidir si dos
        # nombres son comparables. Se arma una vez, acá, para poder explicar
        # POR QUÉ una discrepancia quedó sin auditar.
        vocabulario = {rt.normalizar_nombre(p.nombre) for p in barrios if p.nombre}

        filas = []
        for e in escuelas:
            r = rt.resolver_punto(
                e["longitud"], e["latitud"], barrios, upzs,
                barrio_declarado=e["declarado"], tolerancia_m=tolerancia)
            filas.append({**e, **r})

            # Barrido de fallos silenciosos: cada escuela anota POR QUÉ quedó
            # como quedó. "Sin coordenada" y "cayó fuera de todo polígono" hoy
            # terminan las dos en `sin_poligono`/vacío y exigen acciones
            # opuestas: una la arregla el área con la dirección, la otra es la
            # deuda M22 de geometrías faltantes.
            if r["barrio_estado"] == rt.ESTADO_SIN_COORDENADA:
                diag.anotar("cruce_barrio", NO_INTENTADO, "la escuela no tiene punto")
            elif r["barrio_estado"] == rt.ESTADO_SIN_POLIGONO:
                diag.anotar("cruce_barrio", SIN_HIT,
                            "tiene punto, pero ningún barrio con geometría lo cubre "
                            "(deuda M22: faltan polígonos)")
            else:
                diag.anotar("cruce_barrio", OK)

            if r["upz_codigo"] is not None:
                diag.anotar("cruce_upz", OK,
                            "" if r["upz_metodo"] == "contenida" else "por cercanía al borde")
            elif r["barrio_estado"] == rt.ESTADO_SIN_COORDENADA:
                diag.anotar("cruce_upz", NO_INTENTADO, "la escuela no tiene punto")
            else:
                # Esto NO puede pasar: las 12 UPZ teselan la localidad.
                diag.anotar("cruce_upz", SIN_HIT,
                            "¡con coordenada y sin UPZ! revisa la geometría de `upz`")

            # `discrepancia is None` tiene DOS causas distintas y hay que
            # separarlas: agruparlas fue un fallo silencioso de este mismo
            # contador (66 filas etiquetadas como "vocabulario no comparable"
            # cuando solo 61 lo eran). Una la resuelve el catálogo, la otra la
            # resuelve tener geometría del barrio — no son el mismo problema.
            if r["discrepancia"] is not None:
                diag.anotar("discrepancia", OK)
            elif not e["declarado"]:
                diag.anotar("discrepancia", NO_INTENTADO,
                            "la escuela no declara barrio")
            elif rt.normalizar_nombre(e["declarado"]) not in vocabulario:
                diag.anotar("discrepancia", NO_INTENTADO,
                            "el nombre declarado no existe en el catálogo "
                            "(vocabulario no comparable: el área usa el nombre "
                            "popular, el catálogo el catastral)")
            else:
                diag.anotar("discrepancia", SIN_HIT,
                            "el nombre SÍ está en el catálogo, pero no hay barrio "
                            "resuelto contra el cual compararlo")

        # Antes de resumir o escribir: si se cruzaron puntos contra polígonos y
        # no acertó ninguno, eso no es un resultado — es un síntoma, y se frena.
        # Un cruce en cero es exactamente lo que pasó dos veces en esta tarea sin
        # que nada avisara.
        try:
            rt.exigir_cruces(filas, hay_barrios=bool(barrios), hay_upz=bool(upzs))
        except rt.CrucesEnCeroError as e:
            raise CommandError(str(e))

        self._resumen(filas, tolerancia)

        # Al cierre, para que sea lo último que se lee (ESTADO.md §2.4).
        self.stdout.write("")
        for linea in diag.lineas():
            self.stdout.write(linea)
        descuadre = diag.sin_anotar("cruce_barrio", len(escuelas))
        if descuadre:
            self.stdout.write(self.style.ERROR(
                f"  ¡DESCUADRE! {len(escuelas)} escuelas y "
                f"{diag.total('cruce_barrio')} anotadas: hay una rama muda."))

        if opts["reporte"]:
            self._escribir_reporte(opts["reporte"], filas)

        if not aplicar:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN — no se escribió nada. Re-corre con --apply para "
                f"persistir {len(filas)} resoluciones."))
            return

        n = self._escribir(filas)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"APLICADO: {n} escuelas actualizadas."))

    # ── datos ───────────────────────────────────────────────────────────────
    @staticmethod
    def _verificar_columnas():
        """El proyecto no migra: si el DDL 014 no está aplicado, el comando lo
        dice en vez de reventar con un error de columna a mitad del UPDATE."""
        requeridas = {"barrio_declarado", "barrio_resuelto", "barrio_estado",
                      "upz_resuelta", "discrepancia"}
        with connection.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                 WHERE table_name = 'escuela'
            """)
            existentes = {r[0] for r in cur.fetchall()}
        faltan = requeridas - existentes
        if faltan:
            raise CommandError(
                f"A `escuela` le faltan columnas: {', '.join(sorted(faltan))}. "
                f"Aplica antes el script 014_escuela_censo_julio.sql (lo hace Alex, "
                f"con backup). Este comando no aplica DDL.")

    @staticmethod
    def _escuelas() -> list[dict]:
        """El declarado sale de `barrio_declarado` y, si está NULL, del nombre del
        barrio al que apunta `barrio_codigo`. Solo se LEE."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.nombre, e.latitud, e.longitud,
                       COALESCE(NULLIF(TRIM(e.barrio_declarado), ''), b.nombre) AS declarado,
                       e.barrio_codigo
                  FROM escuela e
             LEFT JOIN barrio b ON b.codigo = e.barrio_codigo
              ORDER BY e.id
            """)
            # La clave del declarado NO se llama `barrio_codigo` a propósito: ese
            # nombre lo ocupa el resultado del resolver al fusionar los dicts, y
            # confundirlos sería escribir el declarado como si fuera el resuelto.
            return [{"id": i, "nombre": n,
                     "latitud": float(la) if la is not None else None,
                     "longitud": float(lo) if lo is not None else None,
                     "declarado": d, "declarado_codigo": bc}
                    for i, n, la, lo, d, bc in cur.fetchall()]

    # ── salida ──────────────────────────────────────────────────────────────
    def _resumen(self, filas, tolerancia):
        estados: dict = {}
        for f in filas:
            estados[f["barrio_estado"]] = estados.get(f["barrio_estado"], 0) + 1

        con_coord = sum(1 for f in filas if f["latitud"] is not None
                        and f["longitud"] is not None)
        con_upz = sum(1 for f in filas if f["upz_codigo"] is not None)
        upz_cercana = sum(1 for f in filas if f["upz_metodo"] == "cercana")
        discrepan = sum(1 for f in filas if f["discrepancia"] is True)
        sin_auditar = sum(1 for f in filas if f["discrepancia"] is None)
        solapes = sum(1 for f in filas if (f["barrio_candidatos"] or 0) > 1)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"barrio_estado (tolerancia de borde: {tolerancia:.0f} m)"))
        for estado in rt.ESTADOS_BARRIO:
            n = estados.get(estado, 0)
            pct = 100 * n / len(filas) if filas else 0
            self.stdout.write(f"  {estado:<16} {n:>5}  ({pct:4.1f} %)")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Ubicación administrativa"))
        self.stdout.write(f"  con coordenada       {con_coord:>5}")
        self.stdout.write(f"  con UPZ resuelta     {con_upz:>5}"
                          + ("  ← toda coordenada quedó ubicada"
                             if con_upz == con_coord else ""))
        if con_upz != con_coord:
            self.stdout.write(self.style.ERROR(
                f"  ¡{con_coord - con_upz} con coordenada y SIN UPZ! La regla dice "
                f"que eso no puede pasar; revisa la geometría de `upz`."))
        if upz_cercana:
            self.stdout.write(f"    de esas, por cercanía al borde: {upz_cercana}")
        if solapes:
            self.stdout.write(f"  puntos en más de un barrio: {solapes} "
                              f"(gana el polígono más pequeño)")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Discrepancia declarado vs. resuelto"))
        self.stdout.write(f"  discrepan            {discrepan:>5}")
        self.stdout.write(f"  coinciden            {len(filas) - discrepan - sin_auditar:>5}")
        self.stdout.write(f"  no auditable         {sin_auditar:>5}  "
                          f"(sin declarado o sin resuelto)")

        muestras = [f for f in filas if f["discrepancia"] is True][:10]
        if muestras:
            self.stdout.write("\n  Primeras discrepancias:")
            for f in muestras:
                self.stdout.write(
                    f"    escuela {f['id']:<5} declarado={f['declarado']!r} "
                    f"→ resuelto={f['barrio_nombre']!r} "
                    f"(barrio {f['barrio_codigo']}, {f['barrio_estado']})")

    @staticmethod
    def _escribir_reporte(ruta, filas):
        with open(ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["escuela_id", "latitud", "longitud", "barrio_declarado",
                        "barrio_declarado_codigo", "barrio_resuelto_codigo",
                        "barrio_resuelto_nombre", "barrio_estado", "distancia_m",
                        "candidatos", "upz_resuelta", "upz_metodo", "discrepancia"])
            for f in filas:
                w.writerow([f["id"], f["latitud"], f["longitud"], f["declarado"],
                            f["declarado_codigo"], f["barrio_codigo"],
                            f["barrio_nombre"], f["barrio_estado"],
                            f["barrio_distancia_m"], f["barrio_candidatos"],
                            f["upz_codigo"], f["upz_metodo"], f["discrepancia"]])

    @staticmethod
    def _escribir(filas) -> int:
        """Un UPDATE por escuela, en una sola transacción. Solo las 4 columnas de
        resolución: cualquier otra es de la carga del censo y no es de acá."""
        n = 0
        with transaction.atomic():
            with connection.cursor() as cur:
                for f in filas:
                    cur.execute("""
                        UPDATE escuela
                           SET barrio_resuelto = %s,
                               barrio_estado   = %s,
                               upz_resuelta    = %s,
                               discrepancia    = %s
                         WHERE id = %s
                    """, [
                        str(f["barrio_codigo"]) if f["barrio_codigo"] is not None else None,
                        f["barrio_estado"],
                        str(f["upz_codigo"]) if f["upz_codigo"] is not None else None,
                        f["discrepancia"],
                        f["id"],
                    ])
                    n += cur.rowcount
        return n
