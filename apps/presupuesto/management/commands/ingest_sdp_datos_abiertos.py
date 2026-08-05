"""Ingesta de Planeación (SEGPLAN / Datos Abiertos SDP-PDL) → tabla espejo.

Descarga el CSV oficial de Proyectos de Desarrollo Local (mapa-inversiones),
filtra a Kennedy, normaliza y hace UPSERT idempotente en `sdp_meta_oficial`.
Solo-lectura respecto a la cadena interna (no toca proyecto/metas/contrato).

Uso:
    docker exec innova_k python manage.py ingest_sdp_datos_abiertos            # seco
    docker exec innova_k python manage.py ingest_sdp_datos_abiertos --write    # persiste
    docker exec innova_k python manage.py ingest_sdp_datos_abiertos
    docker exec innova_k python manage.py ingest_sdp_datos_abiertos --csv /ruta/local.csv

Idempotente: UNIQUE(vigencia, codigo_proyecto, plan_meta_producto_id,
actividad_codigo) + hash_fila → reejecutar no duplica; si la fila cambió, UPDATE.
Requiere que exista la tabla (script 007_sdp_oficial.sql) salvo sin --write.
"""
import csv
import hashlib
import io
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

PDL_URL = ("https://adlsinversionesbogota.blob.core.windows.net/opendata/"
           "DatosAbiertosProyectosDesarrolloLocal.csv")
KENNEDY_ID = "08"
FUENTE = "DatosAbiertosProyectosDesarrolloLocal"


def _norm_codigo(v):
    """Normaliza el código de proyecto: quita ceros a la izquierda y espacios.
    '0002780' → '2780'. Deja como texto. Vacío/no numérico → tal cual .strip()."""
    s = (v or "").strip()
    return str(int(s)) if s.isdigit() else s


def _num(v):
    """Parsea número US ('1000.0', '68530.93') a float o None."""
    s = (v or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int(v):
    s = (v or "").strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


# Mapa columna CSV → (campo tabla, parser). Columnas verificadas 2026-07.
def _fila_a_dict(r):
    return {
        "vigencia": _int(r.get("Vigencia")),
        "codigo_proyecto": _norm_codigo(r.get("CodigoProyecto")),
        "codigo_bpin": (r.get("CodigoBPIN") or "").strip() or None,
        "nombre_proyecto": (r.get("NombreProyecto") or "").strip() or None,
        "estado_proyecto": (r.get("EstadoProyecto") or "").strip() or None,
        "id_localidad": (r.get("IdLocalidad") or "").strip() or "08",
        "localidad": (r.get("Localidad") or "").strip() or None,
        "sector": (r.get("NombreSector") or "").strip() or None,
        "total_programado": _num(r.get("TotalProgramado")),
        "total_comprometido": _num(r.get("TotalComprometido")),
        "total_girado": _num(r.get("TotalGirado")),
        "codigo_objetivo": (r.get("CodigoObjetivoPlanDesarrollo") or "").strip() or None,
        "objetivo": (r.get("ObjetivoPlanDesarrollo") or "").strip() or None,
        "codigo_programa": (r.get("CodigoProgramaPlanDesarrollo") or "").strip() or None,
        "programa": (r.get("ProgramaPlanDesarrollo") or "").strip() or None,
        "plan_meta_producto_id": (r.get("PlanMetaProductoId") or "").strip(),
        "plan_meta_producto_nombre": (r.get("PlanMetaProductoNombre") or "").strip() or None,
        "actividad_codigo": (r.get("ActividadCodigo") or "").strip() or "",
        "actividad_nombre": (r.get("ActividadNombre") or "").strip() or None,
        "tipo_anualizacion": (r.get("ActividadTipoAnualizacion") or "").strip() or None,
        "magnitud_programada": _num(r.get("ActividadMagnitudProgramadaTotal")),
        "magnitud_comprometida": _num(r.get("ActividadMagnitudComprometidoTotal")),
        "magnitud_entregada": _num(r.get("ActividadMagnitudEntregadoTotal")),
        "pct_comprometido": _num(r.get("ActividadMagnitudPorcentajeComprometidoTotal")),
        "pct_entregado": _num(r.get("ActividadMagnitudPorcentajeEntregadoTotal")),
        "valor_programado": _num(r.get("ActividadValorProgramadoTotal")),
        "valor_comprometido": _num(r.get("ActividadValorComprometidoTotal")),
        "valor_girado": _num(r.get("ActividadValorGiradoTotal")),
        "avance_financiero": _num(r.get("AvanceFinanciero")),
    }


def _hash(d):
    base = "|".join(str(d.get(k)) for k in sorted(d))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


COLS = [
    "vigencia", "codigo_proyecto", "codigo_bpin", "nombre_proyecto", "estado_proyecto",
    "id_localidad", "localidad", "sector", "total_programado", "total_comprometido",
    "total_girado", "codigo_objetivo", "objetivo", "codigo_programa", "programa",
    "plan_meta_producto_id", "plan_meta_producto_nombre", "actividad_codigo",
    "actividad_nombre", "tipo_anualizacion", "magnitud_programada", "magnitud_comprometida",
    "magnitud_entregada", "pct_comprometido", "pct_entregado", "valor_programado",
    "valor_comprometido", "valor_girado", "avance_financiero",
]


class Command(BaseCommand):
    help = "Ingesta de Planeación SDP-PDL (Kennedy) a la tabla espejo sdp_meta_oficial."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe en la BD. Sin el flag no persiste (default seco).")
        parser.add_argument("--csv", type=str, default=None,
                            help="Ruta a un CSV local en vez de descargar de la URL.")

    def handle(self, *args, **opts):
        # 1) obtener el contenido
        if opts["csv"]:
            self.stdout.write(f"Leyendo CSV local: {opts['csv']}")
            with open(opts["csv"], "r", encoding="utf-8-sig") as fh:
                texto = fh.read()
        else:
            self.stdout.write(f"Descargando {PDL_URL} …")
            try:
                with urllib.request.urlopen(PDL_URL, timeout=90) as r:
                    texto = r.read().decode("utf-8-sig")
            except Exception as e:
                self.stderr.write(f"No se pudo descargar: {e!r} "
                                  "(¿el contenedor tiene salida a internet? usar --csv).")
                return

        # 2) parsear + filtrar Kennedy
        reader = csv.DictReader(io.StringIO(texto))
        filas = []
        for r in reader:
            if (r.get("IdLocalidad") or "").strip() != KENNEDY_ID \
               and "KENNEDY" not in (r.get("Localidad") or "").upper():
                continue
            d = _fila_a_dict(r)
            if not d["vigencia"] or not d["codigo_proyecto"] or not d["plan_meta_producto_id"]:
                continue
            filas.append(d)

        self.stdout.write(f"Filas de Kennedy válidas: {len(filas)}")
        metas = {d["plan_meta_producto_id"] for d in filas}
        proys = {d["codigo_proyecto"] for d in filas}
        self.stdout.write(f"  proyectos distintos: {len(proys)}  ·  metas distintas: {len(metas)}")

        if not opts["write"]:
            self.stdout.write(self.style.WARNING("SECO: nada se escribió (usa --write para persistir)."))
            for d in filas[:5]:
                self.stdout.write(f"  ej: proy={d['codigo_proyecto']} meta={d['plan_meta_producto_id']} "
                                  f"vig={d['vigencia']} prog={d['magnitud_programada']} "
                                  f"entreg={d['magnitud_entregada']} anualiz={d['tipo_anualizacion']}")
            return

        # 3) upsert idempotente
        ahora = timezone.now()
        ins = upd = 0
        with connection.cursor() as c:
            for d in filas:
                h = _hash(d)
                c.execute(
                    "SELECT id, hash_fila FROM sdp_meta_oficial "
                    "WHERE vigencia=%s AND codigo_proyecto=%s AND plan_meta_producto_id=%s "
                    "AND actividad_codigo=%s",
                    [d["vigencia"], d["codigo_proyecto"], d["plan_meta_producto_id"], d["actividad_codigo"]],
                )
                row = c.fetchone()
                vals = [d[k] for k in COLS] + [FUENTE, h, ahora]
                if row is None:
                    c.execute(
                        f"INSERT INTO sdp_meta_oficial ({','.join(COLS)},fuente,hash_fila,synced_at) "
                        f"VALUES ({','.join(['%s'] * (len(COLS) + 3))})",
                        vals,
                    )
                    ins += 1
                elif row[1] != h:
                    c.execute(
                        f"UPDATE sdp_meta_oficial SET {','.join(f'{k}=%s' for k in COLS)},"
                        f"fuente=%s,hash_fila=%s,synced_at=%s WHERE id=%s",
                        vals + [row[0]],
                    )
                    upd += 1
        self.stdout.write(self.style.SUCCESS(f"Ingesta OK: {ins} insertadas, {upd} actualizadas, "
                                             f"{len(filas) - ins - upd} sin cambio."))
