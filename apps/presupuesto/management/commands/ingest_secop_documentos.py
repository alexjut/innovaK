"""Catálogo de los estudios previos publicados de cada proceso.

    python manage.py ingest_secop_documentos            # seco
    python manage.py ingest_secop_documentos --write

Esto NO baja PDFs: solo registra qué archivos existen, dónde y de cuándo. La
descarga y la lectura van en `extraer_obligaciones`, aparte, porque son dos
problemas con fallas distintas —el índice falla por red o por filtro; la lectura
falla por el PDF— y mezclarlos hace imposible saber cuál se rompió.

## Dos datasets, y no se parten por año de contrato

    nbae-kzan   «Archivos Descarga Historico 2024»
    dmgg-8hin   «Archivos Descarga Desde 2025»

Se parten por FECHA DE CARGA del archivo, no por vigencia del contrato, así que
se solapan: medido el 2026-10-15, procesos de 2022 aparecen en los dos. Hay que
consultar ambos siempre.

## Lo que se midió antes de escribir esto

7.332 archivos de estudio previo sobre 2.773 procesos —3,5 por proceso—, así que
hay varias versiones del mismo documento y la fecha de carga es lo que las
ordena. De 2020 a 2023 hay CERO: de esos años solo se publicó el expediente
post-contractual. Ver el encabezado del DDL 036.
"""
import hashlib
import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

DATASETS = ("nbae-kzan", "dmgg-8hin")

#: Cómo se reconoce el estudio previo entre los ~51 archivos de un proceso.
#: Es el nombre del archivo, que es lo único que el índice publica además del
#: tamaño: `2. Estudio previo.pdf`, `ESTUDIO PREVIO.pdf`, `160366estudio
#: previo.pdf`. La descripción del dataset trae el mismo nombre repetido.
PATRON = "%ESTUDIO PREVIO%"
CLASE = "estudio_previo"

#: De a 100 procesos por consulta. El dataset tiene 134 millones de filas, así
#: que filtrar por entidad se va en timeout: se filtra por la llave, en lotes.
LOTE = 100


def _consultar(recurso: str, where: str, limite: int = 10000) -> list[dict]:
    q = urllib.parse.urlencode({"$where": where, "$limit": limite})
    url = f"https://www.datos.gov.co/resource/{recurso}.json?{q}"
    with urllib.request.urlopen(url, timeout=240) as r:
        if r.status != 200:
            raise RuntimeError(f"{recurso}: HTTP {r.status}")
        return json.load(r)


def _txt(v):
    if isinstance(v, dict):
        v = v.get("url")
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _entero(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _fecha(v):
    s = _txt(v)
    return s.replace("T", " ")[:26] if s else None


def _hash(d: dict) -> str:
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


class Command(BaseCommand):
    help = "Registra los estudios previos publicados de cada proceso."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe. Sin el flag solo consulta y reporta.")
        parser.add_argument("--limite-procesos", type=int, default=0,
                            help="Solo los N primeros procesos (para probar).")

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            cur.execute("""SELECT DISTINCT proceso_de_compra
                           FROM secop_contrato
                           WHERE proceso_de_compra IS NOT NULL
                           ORDER BY 1""")
            procesos = [r[0] for r in cur.fetchall()]
        if opts["limite_procesos"]:
            procesos = procesos[:opts["limite_procesos"]]
        self.stdout.write(f"▸ {len(procesos)} procesos del espejo por consultar")

        # Llave natural (proceso, id_documento): el mismo archivo aparece en los
        # dos datasets cuando su fecha de carga cae en el solape.
        filas: dict[tuple, dict] = {}
        fallos = 0
        for ds in DATASETS:
            for i in range(0, len(procesos), LOTE):
                lote = procesos[i:i + LOTE]
                lista = ",".join("'" + p.replace("'", "") + "'" for p in lote)
                where = (f"proceso in({lista}) AND "
                         f"upper(nombre_archivo) like '{PATRON}'")
                try:
                    crudas = _consultar(ds, where)
                except Exception as exc:
                    fallos += 1
                    self.stderr.write(self.style.WARNING(
                        f"  {ds} lote {i // LOTE}: {type(exc).__name__}"))
                    continue
                for f in crudas:
                    ident = _entero(f.get("id_documento"))
                    proc = _txt(f.get("proceso"))
                    if not proc or ident is None:
                        continue
                    filas[(proc, ident)] = {
                        "proceso": proc,
                        "id_documento": ident,
                        "numero_contrato": _txt(f.get("n_mero_de_contrato")),
                        "clase": CLASE,
                        "nombre_archivo": _txt(f.get("nombre_archivo")),
                        "extension": (_txt(f.get("extensi_n")) or "").lower() or None,
                        "bytes": _entero(f.get("tamanno_archivo")),
                        "fecha_carga": _fecha(f.get("fecha_carga")),
                        "url_descarga": _txt(f.get("url_descarga_documento")),
                        "fuente": ds,
                    }
            self.stdout.write(f"  {ds}: acumulado {len(filas)} archivos")

        if fallos:
            # Escribir con lotes caídos dejaría «este proceso no tiene estudio
            # previo» cuando lo que pasó es que la consulta falló.
            self.stdout.write(self.style.ERROR(
                f"\n✗ {fallos} lotes fallaron. NO se escribe: un lote perdido se "
                f"leería como «ese proceso no tiene estudio previo», que es un "
                f"falso negativo imposible de distinguir del dato."))
            return

        self._reportar(filas, procesos)
        if not opts["write"]:
            self.stdout.write(self.style.WARNING(
                "\nCORRIDA EN SECO: no se escribió nada. Repita con --write."))
            return
        self._guardar(list(filas.values()))

    def _reportar(self, filas, procesos):
        from collections import Counter
        con = {p for p, _ in filas}
        self.stdout.write(f"\n▸ {len(filas)} archivos sobre {len(con)} procesos")
        self.stdout.write(f"  procesos CON estudio previo: {len(con)} de "
                          f"{len(procesos)} ({100 * len(con) / max(len(procesos), 1):.1f} %)")
        porproc = Counter(p for p, _ in filas)
        if porproc:
            self.stdout.write(
                f"  versiones por proceso: promedio "
                f"{sum(porproc.values()) / len(porproc):.1f} · máximo "
                f"{max(porproc.values())}")
        ext = Counter((f["extension"] or "?") for f in filas.values())
        self.stdout.write(f"  extensiones: {dict(ext.most_common(6))}")
        sin_url = sum(1 for f in filas.values() if not f["url_descarga"])
        if sin_url:
            self.stdout.write(self.style.WARNING(
                f"  {sin_url} sin URL de descarga: no se podrán leer"))

    def _guardar(self, filas):
        ahora = timezone.now()
        cols = ["proceso", "id_documento", "numero_contrato", "clase",
                "nombre_archivo", "extension", "bytes", "fecha_carga",
                "url_descarga", "fuente"]
        nuevas = act = igual = 0
        with connection.cursor() as cur:
            for f in filas:
                h = _hash(f)
                cur.execute("SELECT hash_fila FROM secop_documento "
                            "WHERE proceso = %s AND id_documento = %s",
                            [f["proceso"], f["id_documento"]])
                fila = cur.fetchone()
                if fila and fila[0] == h:
                    igual += 1
                    continue
                if fila:
                    sets = ", ".join(f"{c} = %s" for c in cols)
                    # El estado de extracción se reinicia SOLO si cambió el
                    # archivo: si no, se conserva para no volver a bajar 2.773
                    # PDFs cada noche.
                    cur.execute(
                        f"UPDATE secop_documento SET {sets}, hash_fila = %s, "
                        f"synced_at = %s, extraccion_estado = 'pendiente', "
                        f"extraccion_motivo = NULL "
                        f"WHERE proceso = %s AND id_documento = %s",
                        [f[c] for c in cols] + [h, ahora,
                                                f["proceso"], f["id_documento"]])
                    act += 1
                else:
                    campos = ", ".join(cols + ["hash_fila", "synced_at"])
                    marcas = ", ".join(["%s"] * (len(cols) + 2))
                    cur.execute(
                        f"INSERT INTO secop_documento ({campos}) "
                        f"VALUES ({marcas})",
                        [f[c] for c in cols] + [h, ahora])
                    nuevas += 1
        self.stdout.write(self.style.SUCCESS(
            f"  ESCRITO · nuevas {nuevas} · actualizadas {act} · "
            f"sin cambio {igual}"))
