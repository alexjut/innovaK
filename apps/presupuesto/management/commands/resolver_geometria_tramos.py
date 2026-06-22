"""Resuelve y cachea la geometría (LineString) de los tramos viales desde la
Malla Vial Integral de Bogotá, consultando por CIV (campo MVICIV).

Fuente oficial (SDM/IDU), capa 0 del FeatureServer. Descarga UNA vez y guarda
el GeoJSON LineString en `tramo_vial_contrato.geom` (WGS84). Marca:
  - OK            → geometría encontrada y cacheada.
  - NO_ENCONTRADO → el CIV no existe en la malla (queda para revisión manual).
No inventa geometría.

    python manage.py resolver_geometria_tramos          # solo los pendientes
    python manage.py resolver_geometria_tramos --force   # re-resuelve todos
"""
import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.presupuesto.models import TramoVialContrato

FEATURESERVER = (
    "https://services2.arcgis.com/NEwhEo9GGSHXcRXV/arcgis/rest/services/"
    "Malla_Vial_Integral_Bogota_D_C/FeatureServer/0/query"
)
CIV_FIELD = "MVICIV"
LOTE = 25  # CIVs por petición


class Command(BaseCommand):
    help = "Cachea la geometría de los tramos viales desde la Malla Vial (por CIV)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Re-resuelve todos los tramos, no solo los pendientes.")

    def handle(self, *args, **options):
        qs = TramoVialContrato.objects.filter(civ__isnull=False)
        if not options["force"]:
            qs = qs.exclude(geo_status=TramoVialContrato.OK)
        tramos = list(qs)
        if not tramos:
            self.stdout.write(self.style.SUCCESS("Nada por resolver (todos OK)."))
            return

        civs = sorted({int(t.civ) for t in tramos})
        self.stdout.write(f"Resolviendo {len(tramos)} tramo(s), {len(civs)} CIV únicos…")

        geom_por_civ = {}
        for i in range(0, len(civs), LOTE):
            lote = civs[i:i + LOTE]
            try:
                geom_por_civ.update(self._consultar(lote))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  lote {i//LOTE + 1}: error {type(e).__name__}: {str(e)[:120]}"))

        ahora = timezone.now()
        n_ok = n_no = 0
        no_encontrados = []
        for t in tramos:
            geom = geom_por_civ.get(int(t.civ))
            if geom:
                t.geom = geom
                t.geo_status = TramoVialContrato.OK
                n_ok += 1
            else:
                t.geo_status = TramoVialContrato.NO_ENCONTRADO
                no_encontrados.append(int(t.civ))
                n_no += 1
            t.updated_at = ahora
            t.save(update_fields=["geom", "geo_status", "updated_at"])

        self.stdout.write(self.style.SUCCESS(
            f"Geometría cacheada: {n_ok} OK · {n_no} NO_ENCONTRADO."))
        if no_encontrados:
            self.stdout.write(self.style.WARNING(
                f"  CIV sin geometría (revisión manual): {no_encontrados}"))

    def _consultar(self, civs):
        """Devuelve {civ_int: geojson_geometry} para los CIV del lote."""
        where = f"{CIV_FIELD} IN ({','.join(str(c) for c in civs)})"
        params = {"where": where, "outFields": CIV_FIELD,
                  "returnGeometry": "true", "outSR": "4326", "f": "geojson"}
        url = FEATURESERVER + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "innovaK/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        out = {}
        for feat in data.get("features", []):
            civ_val = feat.get("properties", {}).get(CIV_FIELD)
            geom = feat.get("geometry")
            if civ_val is None or not geom:
                continue
            out[int(round(float(civ_val)))] = geom  # MVICIV es Double
        return out
