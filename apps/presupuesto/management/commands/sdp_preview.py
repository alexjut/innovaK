"""Preview de la conexión con Planeación (SEGPLAN / Datos Abiertos SDP) — SOLO LECTURA.

Consulta la API oficial de Datos Abiertos de Bogotá (CKAN datastore) filtrada a
Kennedy (No_Localidad=8) y la CRUZA contra los proyectos internos de innovaK por
`proyecto.codigo` ⇄ `Codigo_Proyecto`. Muestra qué códigos de meta oficiales
(SEGPLAN) traería y cuáles machean con lo interno — SIN escribir nada en la BD.

Es el paso previo a la ingesta real (tablas espejo): sirve para VER que el
enganche con lo oficial funciona antes de crear tablas o poblar `metas.codigo_meta`.

Uso:
    docker exec innova_k python manage.py sdp_preview
    docker exec innova_k python manage.py sdp_preview --limite 5000

No requiere DDL ni credenciales (dataset público). Requiere salida a internet.
"""
import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection

# Dataset "presupuesto_comprometido_xmeta_pp" (Presupuestos Participativos),
# portal CKAN de Datos Abiertos Bogotá. IDs verificados 2026-07.
CKAN_BASE = "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"
RESOURCE_ID = "7c5d5813-3621-47d7-92bc-fb46957988cb"
KENNEDY = "8"


def _fetch_kennedy(limite):
    """Trae filas de Kennedy paginando la API CKAN. Devuelve lista de dicts."""
    filas = []
    offset = 0
    page = 500
    while len(filas) < limite:
        params = {
            "resource_id": RESOURCE_ID,
            "limit": min(page, limite - len(filas)),
            "offset": offset,
            "filters": json.dumps({"No_Localidad": KENNEDY}),
        }
        url = CKAN_BASE + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        if not data.get("success"):
            raise RuntimeError(f"CKAN respondió success=false: {data}")
        recs = data["result"]["records"]
        if not recs:
            break
        filas.extend(recs)
        offset += len(recs)
        if len(recs) < params["limit"]:
            break
    return filas


class Command(BaseCommand):
    help = "Preview (solo lectura) de la conexión con Planeación SDP filtrada a Kennedy."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=4000,
                            help="Máximo de filas a traer de la API (default 4000).")

    def handle(self, *args, **opts):
        self.stdout.write("Consultando Datos Abiertos SDP (Kennedy, No_Localidad=8)…")
        try:
            filas = _fetch_kennedy(opts["limite"])
        except Exception as e:
            self.stderr.write(f"No se pudo consultar la API: {e!r}")
            self.stderr.write("(¿el contenedor tiene salida a internet? probar desde el host.)")
            return

        self.stdout.write(f"Filas de Kennedy recibidas: {len(filas)}")
        if not filas:
            return

        # Distintos códigos oficiales
        proy_oficiales = {}   # codigo_proyecto -> nombre
        metas_oficiales = {}  # cod_meta -> descripcion
        for f in filas:
            cp = (f.get("Codigo_Proyecto") or "").strip()
            cm = (f.get("Cod_meta_proyecto_extendida") or "").strip()
            if cp:
                proy_oficiales.setdefault(cp, f.get("Entidad") or "")
            if cm:
                metas_oficiales.setdefault(cm, (f.get("Meta_proyecto") or "")[:60])

        # Lo interno de innovaK
        with connection.cursor() as c:
            c.execute("SELECT codigo FROM proyecto WHERE codigo IS NOT NULL")
            proy_internos = {str(r[0]).strip() for r in c.fetchall()}

        match = sorted(set(proy_oficiales) & proy_internos)
        solo_oficial = sorted(set(proy_oficiales) - proy_internos)
        solo_interno = sorted(proy_internos - set(proy_oficiales))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== CRUCE POR CÓDIGO DE PROYECTO ==="))
        self.stdout.write(f"Proyectos oficiales (SDP) en Kennedy: {len(proy_oficiales)}")
        self.stdout.write(f"Proyectos internos (innovaK):         {len(proy_internos)}")
        self.stdout.write(self.style.SUCCESS(f"MACHEAN por código:                   {len(match)}  → {match}"))
        self.stdout.write(f"Solo en SDP (falta cargar en innovaK): {len(solo_oficial)}")
        self.stdout.write(f"Solo en innovaK (no en este dataset):  {len(solo_interno)}  → {solo_interno[:15]}")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== CÓDIGOS DE META OFICIALES (SEGPLAN) para Kennedy ==="))
        self.stdout.write(f"Total metas oficiales distintas: {len(metas_oficiales)}")
        for cm in sorted(metas_oficiales)[:15]:
            self.stdout.write(f"  {cm}  ·  {metas_oficiales[cm]}")
        if len(metas_oficiales) > 15:
            self.stdout.write(f"  … (+{len(metas_oficiales) - 15} más)")

        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            "Esto es SOLO PREVIEW (nada se escribió). El siguiente paso es la ingesta "
            "real a las tablas espejo + poblar metas.codigo_meta con estos códigos."))
