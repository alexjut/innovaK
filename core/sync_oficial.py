"""Base común para los comandos de sincronización de fuentes oficiales (C3).

Hoy cada comando de sync reimplementa a mano lo mismo: el flag de escritura, el
hash por fila para saltar UPDATEs, y el upsert. Esta clase base lo unifica, que
es el objetivo de C3 ("seco por defecto + --write; upsert en una sentencia; las
mismas columnas espejo en toda tabla espejo").

Un comando de sync hereda de `SyncOficialCommand` y usa `self.upsert(...)`:

    class Command(SyncOficialCommand):
        fuente_licencia = "SCJ"

        def handle(self, *a, **o):
            filas = self._descargar()          # lista de dicts
            if not o["write"]:
                self.stdout.write("SECO: no se escribió."); return
            with connection.cursor() as cur:
                n = self.upsert(cur, "cai", "id",
                                ["id", "nombre", "lat", "lon"], filas,
                                fuente="SCJ")

`upsert` arma UN solo `INSERT ... ON CONFLICT (clave) DO UPDATE SET ... ` con
`execute_values`, e inyecta uniformemente las columnas espejo: `synced_at`
siempre, y `fuente`/`hash_fila`/`fecha_fuente` según se pidan. Así toda tabla
espejo se escribe igual y con la misma trazabilidad.

**Migración incremental:** cada comando se pasa a esta base por separado y se
verifica corriendo su sync (pegan a servicios externos y escriben en la BD
compartida, así que no se migran a ciegas). El helper de aquí está probado en
aislamiento (ver apps/presupuesto/tests/test_sync_base.py): se comprueba el SQL
que genera sin tocar la BD.
"""
import hashlib
import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from psycopg2.extras import execute_values


class SyncOficialCommand(BaseCommand):
    #: clave en core.licencias.LICENCIAS; la subclase la fija para atribuir.
    fuente_licencia = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--write", action="store_true",
            help="Escribe en la BD. Sin el flag no persiste (default seco).")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def hash_fila(datos: dict) -> str:
        """SHA-256 determinista de una fila (claves ordenadas).

        Igual entrada → igual hash, independiente del orden de las claves. Sirve
        para saltar el UPDATE cuando el dato no cambió respecto a la BD.
        """
        payload = json.dumps(datos, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def upsert(self, cursor, tabla, clave, columnas, filas, *,
               fuente=None, fecha_fuente=None, con_hash=True, where=None):
        """Un solo INSERT ... ON CONFLICT (clave) DO UPDATE con execute_values.

        - `clave`: str o lista de columnas del ON CONFLICT (debe(n) estar en
          `columnas`, porque también se insertan).
        - `columnas`: columnas de datos, incluida la clave.
        - `filas`: lista de dicts con esas columnas.
        - `where`: fragmento SQL para el `WHERE` del `DO UPDATE`, sin la
          palabra `WHERE`. **No es decoración: es lo que evita pisar filas que
          no son de la fuente.** `sync_cai` lo necesita
          (`where="cai.fuente = 'SCJ'"`) porque los CAI móviles los carga
          Seguridad a mano con `fuente='MANUAL'`, y sin este guardia la
          siguiente corrida del sync los convertiría en fijos. Al migrar un
          comando a esta base, **revisa si su upsert tenía un WHERE antes de
          borrarlo**: perderlo no rompe nada visible, solo destruye datos del
          área en la corrida siguiente.

        Inyecta `synced_at`=ahora siempre; `fuente`/`hash_fila`/`fecha_fuente`
        según se pasen. El DO UPDATE cubre todas las columnas menos la clave.
        Devuelve el nº de filas enviadas.
        """
        filas = list(filas)
        if not filas:
            return 0
        ahora = timezone.now()
        cols = list(columnas)
        clave = [clave] if isinstance(clave, str) else list(clave)

        # Columnas espejo, en orden fijo (debe coincidir con el armado de valores).
        espejo = ["synced_at"]
        if fuente is not None:
            espejo.append("fuente")
        if con_hash:
            espejo.append("hash_fila")
        if fecha_fuente is not None:
            espejo.append("fecha_fuente")

        all_cols = cols + espejo
        set_cols = [c for c in all_cols if c not in clave]
        sql = (
            f"INSERT INTO {tabla} ({', '.join(all_cols)}) VALUES %s "
            f"ON CONFLICT ({', '.join(clave)}) DO UPDATE SET "
            + ", ".join(f"{c} = EXCLUDED.{c}" for c in set_cols)
        )
        if where:
            sql += f" WHERE {where}"

        valores = []
        for f in filas:
            fila = [f.get(c) for c in cols]
            fila.append(ahora)
            if fuente is not None:
                fila.append(fuente)
            if con_hash:
                fila.append(self.hash_fila({c: f.get(c) for c in cols}))
            if fecha_fuente is not None:
                fila.append(fecha_fuente)
            valores.append(tuple(fila))

        execute_values(cursor, sql, valores)
        return len(valores)
