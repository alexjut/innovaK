"""Propone coordenadas para las instituciones que están sin ubicar.

## Qué hace y qué NO hace

Busca cada institución por nombre en Nominatim (OpenStreetMap) y guarda el punto
**marcándolo como aproximado** en `observacion`. No pretende reemplazar al área:
pretende que no tenga que ubicar 34 instituciones desde cero, sino revisar y
corregir las que estén mal, que es un trabajo mucho más corto.

Por eso cada fila que toca queda diciendo de dónde salió su coordenada. Una
ubicación sin procedencia es indistinguible de una verificada, y a los seis
meses nadie sabe cuál revisó una persona.

## Dos límites deliberados

1. **El punto es la SEDE PRINCIPAL, no la sede donde estudia el beneficiario.**
   El archivo del área trae el código de la INSTITUCIÓN, no el de la sede. Una
   institución con varias sedes —Tecnisistemas tiene más de una— va a quedar en
   la que Nominatim considere principal, que puede no ser la de Kennedy.

2. **Se descarta lo que caiga fuera de Bogotá y la Sabana.** Un nombre genérico
   puede devolver una universidad homónima de otro país, y un punto plausible
   pero equivocado es peor que uno vacío: el vacío se ve, el error no.

## Uso

    python manage.py geolocalizar_instituciones            # seco, solo informa
    python manage.py geolocalizar_instituciones --aplicar
    python manage.py geolocalizar_instituciones --aplicar --rehacer   # también
                                                # las que ya tienen coordenada

Se deshace poniendo las coordenadas en NULL desde la pantalla, o con
`--limpiar-aproximadas`, que solo borra las que puso este comando (las
verificadas por una persona no se tocan).
"""
import json
import time
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.educacion.models import InstitucionEducativa

#: Recuadro de Bogotá + Sabana (incluye Chía, Soacha, Zipaquirá). Un resultado
#: fuera de acá no es la institución que buscamos.
BBOX = {"lat_min": 3.8, "lat_max": 5.3, "lon_min": -74.6, "lon_max": -73.7}

#: Nominatim exige identificarse y pide máximo 1 consulta por segundo.
USER_AGENT = "innovaK/1.0 (Alcaldia Local de Kennedy - sistema interno)"
PAUSA_SEG = 1.1

MARCA = "Ubicación aproximada (OpenStreetMap)"


def _consultar(texto: str):
    q = urllib.parse.urlencode({"q": texto, "format": "json", "limit": 1})
    req = urllib.request.Request(
        "https://nominatim.openstreetmap.org/search?" + q,
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as r:
        datos = json.load(r)
    if not datos:
        return None
    d = datos[0]
    return float(d["lat"]), float(d["lon"]), d.get("display_name", "")


def geocodificar(nombre: str):
    """Devuelve `(lat, lon, descripcion)` o `(None, None, motivo)`.

    Dos intentos: primero acotando a Bogotá —donde está la enorme mayoría— y
    luego a Colombia, que es lo que rescata a las de la Sabana (La Sabana está
    en Chía, fuera del Distrito).
    """
    motivo = "sin resultados"
    for sufijo in (", Bogotá, Colombia", ", Colombia"):
        try:
            r = _consultar(nombre + sufijo)
        except Exception as exc:  # noqa: BLE001 — red: se reporta, no se cae
            return None, None, f"error de red ({exc.__class__.__name__})"
        time.sleep(PAUSA_SEG)
        if not r:
            continue
        lat, lon, desc = r
        if not (BBOX["lat_min"] <= lat <= BBOX["lat_max"]
                and BBOX["lon_min"] <= lon <= BBOX["lon_max"]):
            # Un resultado fuera del recuadro descarta ESE intento, no la
            # búsqueda: el primero devolvió una homónima en España para
            # UNIMINUTO, y abortar ahí dejaba sin probar el segundo.
            motivo = f"resultado fuera de Bogotá y la Sabana ({desc[:50]})"
            continue
        return lat, lon, desc
    return None, None, motivo


class Command(BaseCommand):
    help = ("Propone coordenadas para las instituciones sin ubicar. "
            "Seco por defecto: exige --aplicar para escribir.")

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true",
                            help="Escribe de verdad. Sin esto solo informa.")
        parser.add_argument("--rehacer", action="store_true",
                            help="Incluye las que YA tienen coordenada aproximada.")
        parser.add_argument("--limpiar-aproximadas", action="store_true",
                            help="Borra solo las coordenadas que puso este comando.")
        parser.add_argument("--limite", type=int, default=0,
                            help="Máximo de instituciones a procesar (0 = todas).")

    def handle(self, *args, **opts):
        if opts["limpiar_aproximadas"]:
            return self._limpiar(opts["aplicar"])

        qs = InstitucionEducativa.objects.filter(activa=True)
        if opts["rehacer"]:
            # Las verificadas por una persona NO se rehacen: no llevan la marca.
            qs = qs.filter(latitud__isnull=True) | qs.filter(observacion__contains=MARCA)
        else:
            qs = qs.filter(latitud__isnull=True)
        qs = qs.distinct().order_by("nombre")
        if opts["limite"]:
            qs = qs[:opts["limite"]]

        total = qs.count()
        self.stdout.write(f"{total} institución(es) por ubicar. "
                          f"{'APLICANDO' if opts['aplicar'] else 'SECO (no escribe)'}\n")

        ubicadas = fallidas = 0
        for inst in qs:
            lat, lon, detalle = geocodificar(inst.nombre)
            if lat is None:
                fallidas += 1
                self.stdout.write(self.style.WARNING(
                    f"  ✗ {inst.nombre[:44]:<44} {detalle}"))
                continue
            ubicadas += 1
            self.stdout.write(
                f"  ✓ {inst.nombre[:44]:<44} {lat:.5f}, {lon:.5f}  {detalle[:46]}")
            if opts["aplicar"]:
                with transaction.atomic():
                    inst.latitud, inst.longitud = round(lat, 6), round(lon, 6)
                    inst.observacion = (
                        f"{MARCA} el {inst.updated_at:%Y-%m-%d} a partir del nombre. "
                        "Es la SEDE PRINCIPAL, no necesariamente donde estudia el "
                        "beneficiario. Verifíquela y corrija el punto si hace falta.")
                    inst.save(update_fields=["latitud", "longitud", "observacion",
                                             "updated_at"])

        self.stdout.write(self.style.SUCCESS(
            f"\n{ubicadas} ubicadas · {fallidas} sin resolver"))
        if not opts["aplicar"]:
            self.stdout.write(self.style.WARNING("SECO: no se escribió nada."))
        elif ubicadas:
            self.stdout.write(
                "Todas quedaron marcadas como APROXIMADAS. El área las revisa y "
                "corrige desde /app/educacion/instituciones.")

    def _limpiar(self, aplicar: bool):
        qs = InstitucionEducativa.objects.filter(observacion__contains=MARCA)
        n = qs.count()
        self.stdout.write(f"{n} institución(es) con coordenada aproximada.")
        if not aplicar:
            self.stdout.write(self.style.WARNING("SECO: repita con --aplicar."))
            return
        qs.update(latitud=None, longitud=None, observacion=None)
        self.stdout.write(self.style.SUCCESS(f"{n} coordenadas aproximadas borradas."))
