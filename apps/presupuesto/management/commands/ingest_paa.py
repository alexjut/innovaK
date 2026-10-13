"""Ingesta del Plan Anual de Adquisiciones de Kennedy.

    python manage.py ingest_paa            # seco: consulta y reporta
    python manage.py ingest_paa --write    # persiste
    python manage.py ingest_paa --anio 2026

Dos datasets de datos.gov.co, tres tablas (ver DDL 034):

    b6m4-qgqv  «PAA - Encabezado»  → paa_encabezado
    9sue-ezhx  «PAA»               → paa_item + paa_item_proceso

## El filtro es por código de entidad, NO por NIT

`nit_entidad` = 899999061 lo comparten los fondos de desarrollo local de toda
Bogotá: filtrando por ahí salen 220.981 filas de 33 planes distintos. Por
`codigo_entidad` = 702292459 salen las 6.579 de Kennedy. Medido el 2026-10-13,
y la diferencia no se nota hasta que alguien suma presupuestos de otra
localidad.

Y `nit_entidad` es TEXTO en este dataset aunque los metadatos digan número:
compararlo sin comillas devuelve 400, no cero filas.

## El parseo declara su cobertura

Nada se fuerza. Lo que no se puede parsear queda en `null` y se cuenta en el
resumen de la corrida, para que la cobertura sea un dato medido y no una
promesa.
"""
import hashlib
import json
import re
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

#: Kennedy. Ver el encabezado: por NIT salen 33 planes de toda Bogotá.
CODIGO_ENTIDAD = "702292459"

ENCABEZADO = "b6m4-qgqv"
ITEMS = "9sue-ezhx"

#: El código interno que el área le pone al ítem, al principio de la
#: descripción. La convención CAMBIA cada año y por eso se guarda cuál se
#: reconoció: un `codigo_interno` sin su tipo no se puede comparar entre años.
_CODIGOS = [
    # K-0528_PRESTAR SERVICIOS…           2025 (100 %) y 2026 (81,5 %)
    ("K", re.compile(r"^\s*(K-\d{3,5})\s*[_\-: ]")),
    # ID_900_PRESTAR SERVICIOS…           2024 (100 %)
    ("ID", re.compile(r"^\s*(ID[_ ]?\d{1,5})\s*[_\-: ]")),
    # PS-345-2178-2767-14919 PRESTAR…     2022 (82,1 %). Trae proyecto y meta
    # adentro, así que se guarda completo: partirlo es trabajo de quien lo use.
    ("COMPUESTO", re.compile(r"^\s*([A-Z]{2,4}-\d+(?:-\d+){2,})\s")),
    # INV-061 AUNAR ESFUERZOS…            2022, la minoría
    ("SIMPLE", re.compile(r"^\s*([A-Z]{2,4}-\d{2,5})\s")),
]

#: El SIPSE va entre paréntesis en `procesos_relacionados`, y el origen mete
#: espacios adentro: «(145094 )», «( 142595)». Validado contra el espejo de
#: contratos: 790 de 816 códigos (96,8 %) están en la referencia de un contrato.
_SIPSE = re.compile(r"\(\s*(\d{5,8})\s*\)")

#: La referencia del proceso: FDLK-CD-386-2025, FDLK-SAMC-006-2024.
_REF = re.compile(r"^\s*([A-Z]{2,6}-[A-Z]{2,6}-\d{1,5}-\d{4})")

#: El aviso, dentro de la URL. La MISMA expresión que `ingest_secop_contratos`
#: y que el relleno del DDL 033.
_NOTICE = re.compile(r"noticeUID=([A-Za-z0-9._-]+)", re.I)

_NO_DEFINIDO = {"", "no definido", "no definida", "ninguno", "n/a"}


def _consultar(recurso: str, where: str, limite: int = 2000) -> list[dict]:
    """Páginas de 2.000 hasta que el origen devuelva menos de eso."""
    salida, off = [], 0
    while True:
        q = urllib.parse.urlencode({"$where": where, "$limit": limite,
                                    "$offset": off})
        url = f"https://www.datos.gov.co/resource/{recurso}.json?{q}"
        with urllib.request.urlopen(url, timeout=180) as r:
            if r.status != 200:
                raise RuntimeError(f"{recurso}: HTTP {r.status}")
            lote = json.load(r)
        salida.extend(lote)
        if len(lote) < limite:
            return salida
        off += limite


def _txt(v):
    if isinstance(v, dict):          # url_proceso viene como {'url': …}
        v = v.get("url")
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _entero(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _fecha(v):
    """El origen manda `2025-12-15 17:58:51.6102113` y también ISO con T."""
    s = _txt(v)
    if not s:
        return None
    s = s.replace("T", " ")
    if "." in s:                      # 7 decimales no los acepta Postgres
        cabeza, _, cola = s.partition(".")
        s = f"{cabeza}.{cola[:6]}"
    return s


def _codigo_interno(descripcion):
    """El código del área y la convención con que se reconoció.

    Devuelve `(None, None)` cuando no hay: 2017-2021 y 2023 no lo usan, y eso
    es un hecho del plan de esos años, no un fallo del parseo.
    """
    d = _txt(descripcion) or ""
    for tipo, pat in _CODIGOS:
        m = pat.match(d)
        if m:
            return m.group(1).replace(" ", "_"), tipo
    return None, None


def _hash(d: dict) -> str:
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


class Command(BaseCommand):
    help = "Ingesta del PAA de Kennedy (encabezado + ítems + procesos)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe. Sin el flag solo consulta y reporta.")
        parser.add_argument("--anio", type=int, default=0,
                            help="Solo ese año (para probar).")

    def handle(self, *args, **opts):
        where = f"codigo_entidad = {CODIGO_ENTIDAD}"
        where_items = f"codigo_entidad = '{CODIGO_ENTIDAD}'"
        if opts["anio"]:
            where += f" AND anno = {opts['anio']}"
            where_items += f" AND annio = '{opts['anio']}'"

        self.stdout.write("▸ consultando el encabezado…")
        cab = _consultar(ENCABEZADO, where)
        self.stdout.write(f"  {len(cab)} encabezados")

        self.stdout.write("▸ consultando los ítems…")
        filas = _consultar(ITEMS, where_items)
        self.stdout.write(f"  {len(filas)} filas")
        if not filas:
            self.stdout.write(self.style.WARNING(
                "cero filas: revise el filtro antes de concluir que no hay PAA. "
                "Por NIT salen 220.981 filas de 33 planes distintos."))

        items, procesos = self._armar(filas)
        self._reportar(filas, items, procesos)

        if not opts["write"]:
            self.stdout.write(self.style.WARNING(
                "\nCORRIDA EN SECO: no se escribió nada. Repita con --write."))
            return

        self._guardar(cab, items, procesos)

    # ── armado ──────────────────────────────────────────────────────────────
    def _armar(self, filas):
        """Un ítem por identificador; un proceso por (ítem, referencia cruda).

        Las 246 filas de más NO son duplicados: son el mismo ítem planeado
        apuntando a varios procesos. Colapsarlas por `id` los borraría.
        """
        items: dict[str, dict] = {}
        procesos: dict[tuple, dict] = {}
        for r in filas:
            iid = _txt(r.get("id"))
            if not iid:
                continue
            if iid not in items:
                cod, tipo = _codigo_interno(r.get("descripcion"))
                items[iid] = {
                    "item_id": iid,
                    "identificador_unico": _txt(r.get("identificador_unico")),
                    "anio": _entero(r.get("annio")),
                    "descripcion": _txt(r.get("descripcion")),
                    "codigo_interno": cod,
                    "codigo_interno_tipo": tipo,
                    "fecha_esperada_inicio": _txt(r.get("fecha_esperada_de_inicio")),
                    "fecha_esperada_recepcion": _txt(r.get("fecha_esperada_de_recepcion")),
                    "duracion_esperada": _txt(r.get("duracion_esperada")),
                    "unidad_duracion": _txt(r.get("unidad_de_duracion_esperada")),
                    "origen_recursos": _txt(r.get("origen_recursos")),
                    "valor_total_esperado": _num(r.get("valor_total_esperado")),
                    "valor_presupuesto": _num(r.get("valor_esperado_de_presupuesto")),
                    "requiere_vigencias_fut": _txt(r.get("requiere_vigencias_futuras")),
                    "estado_solicitud": _txt(r.get("estado_de_solicitud_de")),
                    "modalidad": _txt(r.get("modalidad")),
                    "categorias_unspsc": _txt(r.get("categorias_unspsc")),
                    "causal_contratacion": _txt(r.get("causal_de_contratacion")),
                    "grupo_procedimiento": _txt(r.get("grupo_de_procedimiento")),
                    "tipo": _txt(r.get("tipo")),
                    "version_paa": _entero(r.get("version_del_paa")),
                    "fecha_version": _fecha(r.get("fecha_version")),
                    "fecha_carga_paa": _fecha(r.get("fecha_de_carga_del_paa")),
                }

            crudo = (_txt(r.get("procesos_relacionados")) or "")
            definido = crudo.lower() not in _NO_DEFINIDO
            url = _txt(r.get("url_proceso"))
            mref = _REF.match(crudo) if definido else None
            msip = _SIPSE.search(crudo) if definido else None
            mnot = _NOTICE.search(url or "") if url else None
            llave = (items[iid]["item_id"], crudo)
            procesos[llave] = {
                "item_id": iid,
                "proceso_ref_origen": crudo,
                # Tres estados. «declarado» exige referencia parseada —lo
                # pide un CHECK de la tabla—; «ilegible» es el plan nombrando
                # un proceso con un texto que no se puede leer, que no es lo
                # mismo que no tener proceso.
                "proceso_estado": ("declarado" if (definido and mref)
                                   else "ilegible" if definido
                                   else "no_definido"),
                "proceso_ref": mref.group(1) if mref else None,
                "proceso_sipse": msip.group(1) if msip else None,
                "proceso_notice_id": mnot.group(1) if mnot else None,
                "url_proceso": url,
            }
        return items, procesos

    # ── reporte ─────────────────────────────────────────────────────────────
    def _reportar(self, filas, items, procesos):
        from collections import Counter
        self.stdout.write(f"\n▸ {len(items)} ítems · {len(procesos)} procesos "
                          f"(de {len(filas)} filas)")
        extra = len(filas) - len(items)
        self.stdout.write(f"  ítems con varios procesos: {extra} filas de más "
                          f"— se guardan, no se colapsan")

        self.stdout.write("\n  código interno por año y convención:")
        por_anio = Counter((i["anio"], i["codigo_interno_tipo"]) for i in items.values())
        anios = sorted({i["anio"] for i in items.values() if i["anio"]})
        for a in anios:
            tot = sum(1 for i in items.values() if i["anio"] == a)
            con = sum(v for (an, t), v in por_anio.items() if an == a and t)
            tipos = {t: v for (an, t), v in por_anio.items() if an == a and t}
            self.stdout.write(
                f"    {a}: {con:>4}/{tot:<4} {100*con/tot:>5.1f} %  {tipos or ''}")

        decl = [p for p in procesos.values() if p["proceso_estado"] == "declarado"]
        self.stdout.write(f"\n  procesos declarados: {len(decl)} de {len(procesos)} "
                          f"({100*len(decl)/len(procesos):.1f} %)")
        self.stdout.write(
            f"    con SIPSE parseado : "
            f"{sum(1 for p in decl if p['proceso_sipse'])} "
            f"({100*sum(1 for p in decl if p['proceso_sipse'])/max(len(decl),1):.1f} %)")
        self.stdout.write(
            f"    con aviso (notice) : "
            f"{sum(1 for p in decl if p['proceso_notice_id'])} "
            f"({100*sum(1 for p in decl if p['proceso_notice_id'])/max(len(decl),1):.1f} %)")
        rotos = [p["proceso_ref_origen"] for p in procesos.values()
                 if p["proceso_estado"] == "ilegible"]
        sin_proceso = sum(1 for p in procesos.values()
                          if p["proceso_estado"] == "no_definido")
        self.stdout.write(f"    el plan dice que aún no hay proceso: {sin_proceso}")
        if rotos:
            self.stdout.write(self.style.WARNING(
                f"    {len(rotos)} traen texto que NO se pudo parsear como "
                f"referencia; quedan sin clasificar: {rotos[:2]}"))

        # El cruce, que es para lo que existe todo esto.
        notices = {p["proceso_notice_id"] for p in procesos.values()
                   if p["proceso_notice_id"]}
        with connection.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM secop_contrato
                           WHERE proceso_notice_id = ANY(%s)""", [list(notices)])
            enganchan = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM secop_contrato")
            total_ct = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(DISTINCT proceso_notice_id)
                           FROM secop_contrato
                           WHERE proceso_notice_id = ANY(%s)""", [list(notices)])
            notices_ok = cur.fetchone()[0]
        self.stdout.write("\n  el cruce con el espejo de contratos, en las DOS "
                          "direcciones:")
        self.stdout.write(f"    de los {len(notices)} avisos del PAA, están en el "
                          f"espejo: {notices_ok} "
                          f"({100*notices_ok/max(len(notices),1):.1f} %)")
        self.stdout.write(f"    de nuestros {total_ct} contratos, están en el PAA: "
                          f"{enganchan} ({100*enganchan/max(total_ct,1):.1f} %)")

    # ── escritura ───────────────────────────────────────────────────────────
    def _guardar(self, cab, items, procesos):
        ahora = timezone.now()
        n_cab = self._upsert(
            "paa_encabezado", "identificador_unico",
            [self._fila_cab(c) for c in cab], ahora)
        n_it = self._upsert("paa_item", "item_id", list(items.values()), ahora)
        n_pr = self._upsert("paa_item_proceso", ("item_id", "proceso_ref_origen"),
                            list(procesos.values()), ahora)
        for nombre, (nuevas, act, igual) in (("encabezados", n_cab),
                                             ("ítems", n_it),
                                             ("procesos", n_pr)):
            self.stdout.write(self.style.SUCCESS(
                f"  {nombre}: {nuevas} nuevas · {act} actualizadas · "
                f"{igual} sin cambio"))

    def _fila_cab(self, c):
        return {
            "identificador_unico": _txt(c.get("identificador_unico")),
            "id_plan": _txt(c.get("id_plan_anual_de_adquisiciones")),
            "anio": _entero(c.get("anno")),
            "codigo_entidad": _txt(c.get("codigo_entidad")),
            "nombre_entidad": _txt(c.get("nombre_entidad")),
            "mision_vision": _txt(c.get("mision_vision")),
            "perspectiva_estrategica": _txt(c.get("perspectiva_estrategica")),
            "nombre_contacto": _txt(c.get("nombre_contacto")),
            "telefono_contacto": _txt(c.get("telefono_contacto")),
            "correo_contacto": _txt(c.get("correo_contacto")),
            "valor_presupuesto": _num(c.get("valor_presupuesto_general")),
            "presupuesto_menor": _num(c.get("presupuesto_menor_cuantia")),
            "presupuesto_minima": _num(c.get("presupuesto_minima_cuantia")),
            "fecha_publicacion": _fecha(c.get("fecha_de_publicacion")),
            "fecha_creacion": _fecha(c.get("fecha_de_creacion")),
            "fecha_modificacion": _fecha(c.get("fecha_de_ultima_modificacion")),
            "version": _entero(c.get("version")),
            "estado": _txt(c.get("estado")),
            "departamento": _txt(c.get("departamento_paa")),
            "municipio": _txt(c.get("municipio_paa")),
        }

    def _upsert(self, tabla, llave, filas, ahora):
        """Escribe solo lo que CAMBIÓ, comparando por hash de la fila.

        `synced_at` se mueve únicamente cuando la fila cambia: así «3.147 filas
        sin tocar» significa que no cambiaron, no que la ingesta no corrió.
        """
        llaves = (llave,) if isinstance(llave, str) else llave
        nuevas = act = igual = 0
        cols = [c for c in filas[0]] if filas else []
        with connection.cursor() as cur:
            for f in filas:
                h = _hash(f)
                donde = " AND ".join(f"{k} = %s" for k in llaves)
                cur.execute(f"SELECT hash_fila FROM {tabla} WHERE {donde}",
                            [f[k] for k in llaves])
                fila = cur.fetchone()
                if fila and fila[0] == h:
                    igual += 1
                    continue
                if fila:
                    sets = ", ".join(f"{c} = %s" for c in cols)
                    cur.execute(
                        f"UPDATE {tabla} SET {sets}, hash_fila = %s, "
                        f"synced_at = %s WHERE {donde}",
                        [f[c] for c in cols] + [h, ahora]
                        + [f[k] for k in llaves])
                    act += 1
                else:
                    campos = ", ".join(cols + ["hash_fila", "synced_at"])
                    marcas = ", ".join(["%s"] * (len(cols) + 2))
                    cur.execute(
                        f"INSERT INTO {tabla} ({campos}) VALUES ({marcas})",
                        [f[c] for c in cols] + [h, ahora])
                    nuevas += 1
        return nuevas, act, igual
