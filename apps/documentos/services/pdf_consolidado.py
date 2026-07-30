"""Consolidación de anexos en un solo PDF (requisito «tipo Tu Pago»).

El Documento Maestro del Banco de Iniciativas exige que, al descargar la
propuesta, *todos* los anexos se unifiquen automáticamente en un solo
documento final. Este módulo hace exactamente eso y nada más: recibe los
anexos ya en memoria (bytes) y devuelve un PDF único.

    anexos = [
        Anexo("Soporte legal", pdf_bytes),
        Anexo("Cédula del representante", pdf_bytes),
        Anexo("Firma", png_bytes, "image/png"),
    ]
    consolidado = consolidar(anexos, titulo="Propuesta ...", subtitulos=[...])

## Librerías

No se agrega ninguna dependencia: se reusan las dos que el proyecto ya
declara en `requirements.txt` y ya usa para exportar los PDF de asistencia
(`apps/login/views/eventos/asistencia.py`):

- **reportlab** — portada y conversión de imágenes (la firma llega como
  PNG/JPEG desde el canvas HTML5) a una página PDF.
- **PyPDF2** — unión de las páginas de todos los anexos.

## Criterio ante anexos rotos

Un anexo ilegible (PDF corrupto, cifrado con contraseña, imagen que
reportlab no puede abrir) **no aborta el consolidado**: se registra en el
log, se inserta una página de aviso en su lugar y el resto continúa. El
sistema de registro sigue siendo Mongo; este PDF es un derivado.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

MIME_PDF = "application/pdf"
MIMES_IMAGEN = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}

# Márgenes de la página (en puntos, 72 pt = 1 pulgada).
_MARGEN = 2 * 72 / 2.54 * 1.0  # ~2 cm


@dataclass(frozen=True)
class Anexo:
    """Un archivo a incluir en el consolidado.

    `titulo` es lo que se imprime en la portada y en el encabezado de las
    imágenes convertidas; no es el nombre del archivo en disco.
    """
    titulo: str
    contenido: bytes
    mime: str = MIME_PDF

    @property
    def es_pdf(self) -> bool:
        return (self.mime or "").lower().split(";")[0].strip() == MIME_PDF

    @property
    def es_imagen(self) -> bool:
        return (self.mime or "").lower().split(";")[0].strip() in MIMES_IMAGEN


def _pagesize():
    from reportlab.lib.pagesizes import letter
    return letter


def _portada(titulo: str, subtitulos: Sequence[str], anexos: Sequence[Anexo]) -> bytes:
    """Primera página: título, datos de la radicación e índice de anexos."""
    from reportlab.pdfgen import canvas as rl_canvas

    ancho, alto = _pagesize()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(ancho, alto))

    y = alto - _MARGEN
    c.setFont("Helvetica-Bold", 16)
    for linea in _envolver(titulo, 60):
        c.drawString(_MARGEN, y, linea)
        y -= 20

    y -= 6
    c.setFont("Helvetica", 11)
    for sub in subtitulos:
        for linea in _envolver(str(sub), 85):
            c.drawString(_MARGEN, y, linea)
            y -= 15

    y -= 14
    c.setFont("Helvetica-Bold", 12)
    c.drawString(_MARGEN, y, "Anexos incluidos")
    y -= 18
    c.setFont("Helvetica", 11)
    for i, anexo in enumerate(anexos, start=1):
        c.drawString(_MARGEN + 10, y, f"{i}. {anexo.titulo}")
        y -= 15
        if y < _MARGEN:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = alto - _MARGEN

    c.showPage()
    c.save()
    return buf.getvalue()


def _envolver(texto: str, ancho: int) -> list[str]:
    """Corte de línea simple por palabras (evita traer textwrap a la plantilla)."""
    palabras = (texto or "").split()
    if not palabras:
        return [""]
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        if len(actual) + 1 + len(palabra) <= ancho:
            actual = f"{actual} {palabra}"
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def _pagina_aviso(mensaje: str) -> bytes:
    """Página de reemplazo cuando un anexo no se pudo procesar."""
    from reportlab.pdfgen import canvas as rl_canvas

    ancho, alto = _pagesize()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(ancho, alto))
    c.setFont("Helvetica-Bold", 12)
    y = alto - _MARGEN
    for linea in _envolver(mensaje, 80):
        c.drawString(_MARGEN, y, linea)
        y -= 16
    c.showPage()
    c.save()
    return buf.getvalue()


def imagen_a_pdf(anexo: Anexo) -> Optional[bytes]:
    """Convierte una imagen (firma, foto de cédula) en una página PDF.

    Devuelve None si reportlab no puede leer la imagen.
    """
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas

    try:
        imagen = ImageReader(io.BytesIO(anexo.contenido))
        img_w, img_h = imagen.getSize()
    except Exception as exc:  # imagen corrupta o formato no soportado
        logger.warning(
            "consolidado_imagen_ilegible titulo=%r mime=%r error=%s",
            anexo.titulo, anexo.mime, exc,
        )
        return None

    if not img_w or not img_h:
        return None

    ancho, alto = _pagesize()
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(ancho, alto))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(_MARGEN, alto - _MARGEN, anexo.titulo)

    disp_w = ancho - 2 * _MARGEN
    disp_h = alto - 2 * _MARGEN - 30
    escala = min(disp_w / img_w, disp_h / img_h)
    dib_w, dib_h = img_w * escala, img_h * escala
    x = (ancho - dib_w) / 2
    y = (alto - _MARGEN - 30) - dib_h
    c.drawImage(imagen, x, y, width=dib_w, height=dib_h,
                preserveAspectRatio=True, anchor="c", mask="auto")
    c.showPage()
    c.save()
    return buf.getvalue()


def _agregar_pdf(writer, contenido: bytes, titulo: str) -> int:
    """Copia las páginas de `contenido` al writer. Devuelve cuántas agregó."""
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(contenido))
    if reader.is_encrypted:
        # PDF protegido: intento con contraseña vacía (caso común de
        # documentos "solo lectura" escaneados). Si no cede, se salta.
        try:
            reader.decrypt("")
        except Exception:
            pass
        if reader.is_encrypted and not reader.pages:
            raise ValueError("PDF cifrado con contraseña")
    n = 0
    for pagina in reader.pages:
        writer.add_page(pagina)
        n += 1
    if n == 0:
        raise ValueError("PDF sin páginas")
    logger.debug("consolidado_anexo_ok titulo=%r paginas=%d", titulo, n)
    return n


def consolidar(
    anexos: Sequence[Anexo],
    *,
    titulo: str = "Propuesta consolidada",
    subtitulos: Sequence[str] = (),
    portada: bool = True,
) -> Optional[bytes]:
    """Une los anexos en un solo PDF y devuelve sus bytes.

    Devuelve `None` si no hay nada que unir (lista vacía o todos ilegibles
    y sin portada). Nunca lanza excepción por un anexo defectuoso.
    """
    from PyPDF2 import PdfWriter

    anexos = [a for a in (anexos or []) if a and a.contenido]
    if not anexos:
        logger.info("consolidado_sin_anexos titulo=%r", titulo)
        return None

    writer = PdfWriter()

    if portada:
        try:
            _agregar_pdf(writer, _portada(titulo, subtitulos, anexos), "portada")
        except Exception as exc:
            logger.warning("consolidado_portada_falla error=%s", exc)

    incluidos = 0
    for anexo in anexos:
        try:
            if anexo.es_imagen:
                pdf = imagen_a_pdf(anexo)
                if pdf is None:
                    raise ValueError("imagen ilegible")
                _agregar_pdf(writer, pdf, anexo.titulo)
            else:
                # Todo lo que no es imagen se intenta como PDF: el mime
                # puede venir vacío o mal declarado desde el navegador.
                _agregar_pdf(writer, anexo.contenido, anexo.titulo)
            incluidos += 1
        except Exception as exc:
            logger.warning(
                "consolidado_anexo_omitido titulo=%r mime=%r error=%s",
                anexo.titulo, anexo.mime, exc,
            )
            try:
                _agregar_pdf(
                    writer,
                    _pagina_aviso(
                        f"Anexo no legible: {anexo.titulo}. "
                        "El archivo original queda disponible en el repositorio seguro."
                    ),
                    "aviso",
                )
            except Exception:
                pass

    if incluidos == 0 and not portada:
        logger.warning("consolidado_vacio titulo=%r", titulo)
        return None

    salida = io.BytesIO()
    writer.write(salida)
    datos = salida.getvalue()
    logger.info(
        "consolidado_generado titulo=%r anexos=%d incluidos=%d bytes=%d",
        titulo, len(anexos), incluidos, len(datos),
    )
    return datos
