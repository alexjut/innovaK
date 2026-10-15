"""Baja el estudio previo de cada proceso y lee sus obligaciones específicas.

    python manage.py extraer_obligaciones                  # seco, 25 documentos
    python manage.py extraer_obligaciones --write --limite 200
    python manage.py extraer_obligaciones --write --proceso CO1.BDOS.10952264
    python manage.py extraer_obligaciones --write --reextraer   # ignora la caché

Va aparte de `ingest_secop_documentos` porque son dos problemas distintos: ese
habla con el índice y falla por red o por filtro; este baja PDFs y falla por el
PDF. Mezclarlos haría imposible saber cuál se rompió.

## Nunca descarga en caliente

Una petición a `/contratos/{id}/obligaciones/` no baja nada: lee lo que este
comando dejó. Bajar un PDF de 3 MB dentro de una petición HTTP pondría a la API
a depender de que SECOP responda, y la API es lo que alimenta un certificado.

## La caché es el estado del documento

Solo se procesan los que están en `pendiente`. `ingest_secop_documentos` vuelve
a marcar `pendiente` únicamente si el archivo CAMBIÓ (otro hash de fila), así
que una corrida nocturna normal no baja nada. Sin eso serían 2.118 descargas
cada noche para un dato que no se mueve.

## El origen nos puede bloquear, y de hecho lo hizo

Corriendo sin pausa, el 2026-10-15 SECOP cortó el servicio tras ~1.500
descargas: `SSL: UNEXPECTED_EOF_WHILE_READING` en 0,2 s, dirigido a
`community.secop.gov.co` mientras datos.gov.co seguía en 200. Por eso hay una
pausa de 1,5 s entre descargas y un freno a los 8 fallos de conexión seguidos.

Y por eso un fallo de CONEXIÓN deja el documento en `pendiente` en vez de
marcarlo `descarga_fallo`: el que falló fuimos nosotros, y escribir «este
documento no se pudo descargar» sería una afirmación falsa sobre el documento.
Aquella corrida dejó 379 marcados así.

## El User-Agent no es cosmético

La URL de descarga de SECOP responde **403 con el agente por defecto**: la sirve
un Application Gateway de Azure que rechaza a curl y a urllib. Con un
User-Agent de navegador responde 200 y el tamaño coincide al byte con el que
declara el índice. Se manda uno identificable, con el correo de contacto, para
no pasar por un navegador que no somos.

## Se procesa SOLO la versión más reciente

Hay 3 archivos de estudio previo por proceso en promedio y hasta 52 en un caso.
Se lee el más reciente por `fecha_carga`; los demás quedan registrados para
poder auditar cuál se usó, pero no se bajan.
"""
import time
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.presupuesto.services import obligaciones_pdf as O

#: Identificable a propósito: si la Alcaldía satura el servicio de SECOP, que
#: puedan saber quién es y escribir.
AGENTE = ("Mozilla/5.0 (X11; Linux x86_64) innovaK/1.0 "
          "(+https://intranet-public-alk.ngrok.app; alcaldia.kennedy)")

#: 25 MB. El estudio previo más grande de la muestra pesaba 3,2 MB; el tope está
#: para que un archivo equivocado no se trague la memoria del contenedor.
MAX_BYTES = 25 * 1024 * 1024

TIMEOUT_S = 120

#: Pausa entre descargas. No es cortesía decorativa: el 2026-10-15, corriendo
#: sin pausa, SECOP nos bloqueó tras ~1.500 descargas de 3 MB. El síntoma es
#: `SSL: UNEXPECTED_EOF_WHILE_READING` en 0,2 s —el gateway corta el TLS de
#: entrada— y se comprobó que era dirigido a ese host: datos.gov.co y google
#: respondían 200 al mismo tiempo.
PAUSA_S = 1.5

#: Fallos de CONEXIÓN seguidos tras los cuales se aborta la corrida.
#:
#: Sin esto, un bloqueo del origen marca cientos de documentos como «no se pudo
#: descargar», que es una afirmación falsa sobre el documento: el que falló
#: fuimos nosotros. Esa corrida dejó 379 así.
MAX_FALLOS_SEGUIDOS = 8


def _descargar(url: str) -> tuple[bytes | None, str | None]:
    """El PDF, o `(None, motivo)`. Nunca lanza."""
    if not url:
        return None, "sin_url"
    pedido = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Referer": "https://community.secop.gov.co/",
        "Accept": "application/pdf,*/*",
    })
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as r:
            if r.status != 200:
                # Un estado HTTP SÍ habla del documento: 404 es que no está.
                return None, f"http_{r.status}"
            datos = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except Exception as exc:
        # Un fallo de CONEXIÓN no dice nada del documento: dice que el origen
        # no nos está atendiendo. Se marca como NO MEDIDO para que el documento
        # quede pendiente y se reintente, en vez de quedar acusado.
        return None, f"conexion_{type(exc).__name__}"
    if len(datos) > MAX_BYTES:
        return None, "muy_grande"
    if not datos[:5].startswith(b"%PDF"):
        # Pasa cuando el gateway devuelve una página de error con un 200.
        return None, "no_es_pdf"
    return datos, None


def _texto(datos: bytes) -> tuple[str, int, str | None]:
    try:
        import io

        from PyPDF2 import PdfReader
        lector = PdfReader(io.BytesIO(datos))
        paginas = len(lector.pages)
        partes = []
        for p in lector.pages:
            try:
                partes.append(p.extract_text() or "")
            except Exception:
                partes.append("")
        return "\n".join(partes), paginas, None
    except Exception as exc:
        return "", 0, f"lectura_{type(exc).__name__}"


class Command(BaseCommand):
    help = "Extrae las obligaciones específicas del estudio previo de cada proceso."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe. Sin el flag no persiste nada.")
        # 300 por corrida: con la pausa de 1,5 s son unos 12 minutos, que es lo
        # que un trabajo nocturno puede ocupar sin estorbar, y mantiene el ritmo
        # muy por debajo de lo que hizo que el origen nos bloqueara.
        parser.add_argument("--limite", type=int, default=300,
                            help="Cuántos documentos procesar (default 300).")
        parser.add_argument("--proceso", default="",
                            help="Solo ese proceso.")
        parser.add_argument("--reextraer", action="store_true",
                            help="Ignora la caché y vuelve a bajar.")

    def handle(self, *args, **opts):
        filas = self._por_procesar(opts)
        if not filas:
            self.stdout.write("Nada pendiente. Todo extraído.")
            return
        self.stdout.write(f"▸ {len(filas)} documentos por procesar "
                          f"(la versión más reciente de cada proceso)")

        from collections import Counter
        cuenta: Counter = Counter()
        total_obl = 0
        seguidos = 0
        for i, (doc_id, proceso, url, nombre) in enumerate(filas):
            if i:
                time.sleep(PAUSA_S)
            datos, motivo = _descargar(url)
            if datos is None and (motivo or "").startswith("conexion_"):
                # No es del documento: es que el origen no nos atiende. Se deja
                # PENDIENTE y se cuenta aparte; marcarlo como fallo sería
                # escribir una acusación falsa en la base.
                cuenta["origen_no_responde"] += 1
                seguidos += 1
                if seguidos >= MAX_FALLOS_SEGUIDOS:
                    self.stdout.write(self.style.ERROR(
                        f"\n✗ ABORTADO: {seguidos} fallos de conexión seguidos. "
                        f"El origen dejó de atender —probablemente nos limitó— y "
                        f"seguir solo marcaría documentos buenos como fallidos. "
                        f"Los {len(filas) - i - 1} que faltan quedan pendientes."))
                    break
                continue
            seguidos = 0
            if datos is None:
                estado = ("descarga_fallo"
                          if (motivo or "").startswith(("http", "sin_url"))
                          else "no_es_pdf")
                cuenta[estado] += 1
                if opts["write"]:
                    self._marcar(doc_id, estado, motivo, None, None, None)
                continue

            texto, paginas, err = _texto(datos)
            if err or not texto.strip():
                cuenta["sin_texto"] += 1
                if opts["write"]:
                    self._marcar(doc_id, "sin_texto", err or "texto_vacio",
                                 paginas, len(texto), None)
                continue

            cal = O.calidad_pct(texto)
            cruda = O.seccion_cruda(texto)
            if cal > O.CALIDAD_MAXIMA_PCT:
                cuenta["calidad_baja"] += 1
                if opts["write"]:
                    self._marcar(
                        doc_id, "calidad_baja",
                        f"calidad={cal} % supera el umbral de "
                        f"{O.CALIDAD_MAXIMA_PCT} %: el texto trae palabras "
                        f"partidas y se imprimirían así en el certificado",
                        paginas, len(texto), cal, cruda)
                continue

            enc, items, motivo = O.extraer(texto)
            if not items:
                cuenta[motivo or "sin_lista"] += 1
                if opts["write"]:
                    self._marcar(doc_id, self._estado(motivo), motivo,
                                 paginas, len(texto), cal, cruda, enc)
                continue

            cuenta["ok"] += 1
            total_obl += len(items)
            if opts["write"]:
                self._guardar(doc_id, proceso, items, paginas, len(texto),
                              cal, cruda, enc)

        self.stdout.write("\n  resultado:")
        for k, v in cuenta.most_common():
            self.stdout.write(f"    {k:<28} {v:>5}")
        if cuenta["ok"]:
            self.stdout.write(f"    obligaciones leídas          {total_obl:>5} "
                              f"({total_obl / cuenta['ok']:.1f} por documento)")
        if not opts["write"]:
            self.stdout.write(self.style.WARNING(
                "\nCORRIDA EN SECO: no se escribió nada. Repita con --write."))

    @staticmethod
    def _estado(motivo):
        return {"sin_seccion": "sin_seccion",
                "lista_incompleta": "sin_seccion",
                "seccion_sin_lista_numerada": "sin_seccion",
                "sin_texto": "sin_texto"}.get(motivo, "error")

    def _por_procesar(self, opts):
        """La versión más reciente de cada proceso que falte por leer."""
        where = ["d.clase = 'estudio_previo'", "d.extension = 'pdf'"]
        params: list = []
        if not opts["reextraer"]:
            where.append("d.extraccion_estado = 'pendiente'")
        if opts["proceso"]:
            where.append("d.proceso = %s")
            params.append(opts["proceso"])
        with connection.cursor() as cur:
            cur.execute(f"""
                SELECT d.id, d.proceso, d.url_descarga, d.nombre_archivo
                FROM secop_documento d
                JOIN (
                    SELECT proceso,
                           MAX(COALESCE(fecha_carga, '1900-01-01'::timestamptz)) f
                    FROM secop_documento
                    WHERE clase = 'estudio_previo' AND extension = 'pdf'
                    GROUP BY proceso
                ) u ON u.proceso = d.proceso
                   AND COALESCE(d.fecha_carga, '1900-01-01'::timestamptz) = u.f
                WHERE {' AND '.join(where)}
                ORDER BY d.proceso
                LIMIT %s
            """, params + [opts["limite"]])
            return cur.fetchall()

    def _marcar(self, doc_id, estado, motivo, paginas, caracteres, calidad,
                cruda=None, enc=None):
        with connection.cursor() as cur:
            cur.execute("""
                UPDATE secop_documento
                   SET extraccion_estado = %s, extraccion_motivo = %s,
                       extraccion_fecha = %s, paginas = %s, caracteres = %s,
                       calidad_pct = %s, seccion_texto = %s,
                       seccion_encabezado = %s
                 WHERE id = %s
            """, [estado, motivo, timezone.now(), paginas, caracteres,
                  calidad, cruda, enc, doc_id])
            # Si este documento tenía obligaciones de una corrida anterior y
            # ahora no se pueden leer, se BORRAN: dejarlas publicadas sería
            # servir una lista que ya no tiene respaldo.
            cur.execute("DELETE FROM secop_obligacion WHERE documento_id = %s",
                        [doc_id])

    def _guardar(self, doc_id, proceso, items, paginas, caracteres, calidad,
                 cruda, enc):
        with connection.cursor() as cur:
            cur.execute("DELETE FROM secop_obligacion WHERE documento_id = %s",
                        [doc_id])
            for it in items:
                cur.execute("""
                    INSERT INTO secop_obligacion
                        (proceso, documento_id, numero, descripcion, metodo)
                    VALUES (%s, %s, %s, %s, %s)
                """, [proceso, doc_id, it["numero"], it["descripcion"],
                      "lista_numerada_estudio_previo"])
            cur.execute("""
                UPDATE secop_documento
                   SET extraccion_estado = 'ok', extraccion_motivo = NULL,
                       extraccion_fecha = %s, paginas = %s, caracteres = %s,
                       calidad_pct = %s, seccion_texto = %s,
                       seccion_encabezado = %s
                 WHERE id = %s
            """, [timezone.now(), paginas, caracteres, calidad, cruda, enc,
                  doc_id])
