"""Ingiere el dataset DEDICADO de suspensiones de SECOP II (`u99c-7mfm`).

    python manage.py ingest_secop_suspensiones            # seco, no escribe
    python manage.py ingest_secop_suspensiones --write

## Por qué existe, cuando ya tenemos `secop_modificacion`

Porque ese espejo trae el `tipo` INVERTIDO en el par suspensión/reactivación.
Probado fila contra fila, emparejando por contrato Y fecha de aprobación:
donde nuestro espejo dice `SUSPENSIoN`, el dataset oficial dice «Reanudacion»,
y el propio texto lo confirma — «Se procede a REINICIAR el Contrato
CPS-032-2024». Seis de seis.

Por eso la API pública publica ese eje SIN CLASIFICAR y con su advertencia:
fechar una suspensión con ese `tipo` la fecharía el día en que el contrato se
reactivó, en un documento con efectos jurídicos.

## Las dos trampas de este dataset, medidas antes de escribir el comando

**1. Tres de cada cuatro filas son duplicados idénticos.** Para nuestros 3.211
contratos devuelve 5.668 filas, y 4.286 son iguales byte a byte. Guardarlas
daría CUATRO VECES los actos reales.

**2. Los duplicados «distintos» son variantes del mismo acto.** De los 383
grupos que comparten (contrato, tipo, fechas), 382 difieren SOLO en el
propósito: el origen publica el mismo acto varias veces, a veces con el texto y
a veces con «No definido». Se leyeron para comprobarlo.

Por eso se agrupa por la llave natural y se conserva el propósito MÁS
INFORMATIVO. Con esa regla 8 actos de 941 (0,9 %) quedan sin texto útil;
tomando una fila cualquiera serían 384.

## Qué gana

    actos reales ........... 941  (567 suspensiones, 374 reanudaciones)
    contratos cubiertos .... 352
    los que vemos hoy ...... 201
    ganancia ............... +151 contratos

Seco por defecto, como el resto de las ingestas del repo. Idempotente: una
segunda corrida sin cambios no duplica ni una fila.
"""
import hashlib
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

DATASET = "u99c-7mfm"
URL = f"https://www.datos.gov.co/resource/{DATASET}.json"
#: Lotes de contratos por petición. El dataset no tiene columna de entidad, así
#: que NO se puede filtrar por Kennedy: hay que preguntar por nuestras llaves.
#: 100 cabe de sobra en una cadena de consulta.
LOTE = 100

_TIPOS = {"suspension": "SUSPENSION", "reanudacion": "REANUDACION"}


def _codigo(tipo):
    """`Suspension` y `Reanudacion` a nuestro código estable.

    Devuelve None para cualquier otro valor, y el comando lo CUENTA y lo
    reporta en vez de guardarlo: el origen ya cambió una grafía antes, y un
    tipo nuevo tiene que verse, no colarse.
    """
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFKD", (tipo or "").lower())
                if not unicodedata.combining(c)).strip()
    return _TIPOS.get(t)


def _fecha(v):
    return (v or "")[:10] or None


def _informativo(filas):
    """La variante con el propósito más útil del acto.

    «No definido» pierde contra cualquier texto; entre textos, gana el más
    largo. Es la regla que baja los actos sin texto de 384 a 8.
    """
    def peso(f):
        p = (f.get("proposito_de_la_modificacion") or "").strip()
        return (p not in ("", "No definido"), len(p))
    return max(filas, key=peso)


class Command(BaseCommand):
    help = "Espejo del dataset dedicado de suspensiones de SECOP II."

    def add_arguments(self, p):
        p.add_argument("--write", action="store_true",
                       help="Escribe. Sin esta bandera no toca la base.")
        p.add_argument("--limite-contratos", type=int, default=None,
                       help="Solo los primeros N contratos. Para ensayar.")

    def handle(self, *a, **o):
        ok, warn, err = self.style.SUCCESS, self.style.WARNING, self.style.ERROR

        with connection.cursor() as c:
            c.execute("SELECT id_contrato FROM secop_contrato "
                      "WHERE id_contrato IS NOT NULL ORDER BY id_contrato")
            ids = [r[0] for r in c.fetchall()]
        if o["limite_contratos"]:
            ids = ids[: o["limite_contratos"]]
        self.stdout.write(f"Contratos del espejo a consultar: {len(ids):,}")

        crudas, fallos = [], 0
        for i in range(0, len(ids), LOTE):
            lote = ids[i:i + LOTE]
            cond = "id_contrato in (%s)" % ",".join("'%s'" % x for x in lote)
            q = urllib.parse.urlencode({"$where": cond, "$limit": 50000})
            try:
                with urllib.request.urlopen(f"{URL}?{q}", timeout=90) as r:
                    crudas.extend(json.load(r))
            except Exception as exc:
                fallos += 1
                self.stdout.write(err(f"  lote {i // LOTE}: {type(exc).__name__}"))
        if fallos:
            # Un lote perdido es cobertura perdida, y callarlo haría ver la
            # ingesta como completa. Se dice y se aborta la escritura.
            self.stdout.write(err(
                f"\n{fallos} lotes fallaron. NO se escribe: una ingesta parcial "
                "que se presenta como completa es peor que no correrla."))
            return

        self.stdout.write(f"Filas que devuelve el origen: {len(crudas):,}")
        unicas = list({json.dumps(f, sort_keys=True): f for f in crudas}.values())
        self.stdout.write(
            f"  duplicados idénticos descartados: {len(crudas) - len(unicas):,} "
            f"({100 * (len(crudas) - len(unicas)) / max(len(crudas), 1):.1f} %)")

        # Agrupar por la llave natural y quedarse con la mejor variante.
        grupos, sin_tipo = defaultdict(list), Counter()
        for f in unicas:
            cod = _codigo(f.get("tipo"))
            if cod is None:
                sin_tipo[f.get("tipo")] += 1
                continue
            grupos[(f["id_contrato"], cod,
                    _fecha(f.get("fecha_de_creacion")),
                    _fecha(f.get("fecha_de_aprobacion")))].append(f)

        if sin_tipo:
            self.stdout.write(warn(
                f"\n  TIPOS QUE NO RECONOZCO, no se guardan: {dict(sin_tipo)}\n"
                "  El origen cambió. Revisar antes de confiar en el conteo."))

        actos = []
        for (idc, cod, fcre, fapr), filas in grupos.items():
            f = _informativo(filas)
            prop = (f.get("proposito_de_la_modificacion") or "").strip() or None
            if prop == "No definido":
                prop = None
            actos.append({
                "id_contrato": idc, "tipo_codigo": cod,
                "tipo_origen": f.get("tipo"),
                "fecha_creacion": fcre, "fecha_aprobacion": fapr,
                "proposito": prop,
                "contrato_fecha_inicio": _fecha(f.get("fecha_de_inicio_del_contrato")),
                "contrato_fecha_fin": _fecha(f.get("fecha_de_fin_del_contrato")),
                "filas_origen": len(filas),
            })
            actos[-1]["hash_fila"] = hashlib.sha256(
                json.dumps({k: v for k, v in actos[-1].items()
                            if k != "filas_origen"}, sort_keys=True).encode()
            ).hexdigest()

        por_tipo = Counter(a["tipo_codigo"] for a in actos)
        sin_prop = sum(1 for a in actos if not a["proposito"])
        self.stdout.write(ok(f"\nActos reales: {len(actos):,}"))
        self.stdout.write(f"  por tipo: {dict(por_tipo)}")
        self.stdout.write(f"  contratos cubiertos: {len({a['id_contrato'] for a in actos}):,}")
        self.stdout.write(f"  sin propósito útil: {sin_prop} "
                          f"({100 * sin_prop / max(len(actos), 1):.1f} %)")

        if not o["write"]:
            self.stdout.write(warn(
                "\nCORRIDA EN SECO: no se escribió nada. Repita con --write."))
            return

        nuevas = cambiadas = iguales = 0
        with transaction.atomic():
            with connection.cursor() as c:
                for a in actos:
                    c.execute("""
                        SELECT id, hash_fila FROM secop_suspension
                        WHERE id_contrato = %s AND tipo_codigo = %s
                          AND COALESCE(fecha_creacion,   DATE '1900-01-01') = COALESCE(%s::date, DATE '1900-01-01')
                          AND COALESCE(fecha_aprobacion, DATE '1900-01-01') = COALESCE(%s::date, DATE '1900-01-01')
                    """, [a["id_contrato"], a["tipo_codigo"],
                          a["fecha_creacion"], a["fecha_aprobacion"]])
                    fila = c.fetchone()
                    campos = ("id_contrato", "tipo_origen", "tipo_codigo",
                              "fecha_creacion", "fecha_aprobacion", "proposito",
                              "contrato_fecha_inicio", "contrato_fecha_fin",
                              "filas_origen", "hash_fila")
                    vals = [a[k] for k in campos]
                    if fila is None:
                        c.execute(
                            "INSERT INTO secop_suspension (%s) VALUES (%s)"
                            % (",".join(campos), ",".join(["%s"] * len(campos))),
                            vals)
                        nuevas += 1
                    elif fila[1] != a["hash_fila"]:
                        c.execute(
                            "UPDATE secop_suspension SET %s, synced_at = now() WHERE id = %%s"
                            % ",".join(f"{k} = %s" for k in campos),
                            vals + [fila[0]])
                        cambiadas += 1
                    else:
                        iguales += 1

        self.stdout.write(ok(
            f"\nESCRITO · nuevas {nuevas:,} · actualizadas {cambiadas:,} · "
            f"sin cambio {iguales:,}"))
        self.stdout.write(
            "Una segunda corrida sin novedades debe dar nuevas 0 y "
            "actualizadas 0: es la prueba de que no duplica.")
