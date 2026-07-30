"""Tests del consolidado PDF «tipo Tu Pago» (sin red, sin BD).

El requisito del Documento Maestro es que al descargar la propuesta TODOS
los anexos queden unidos en un solo PDF. Lo que se blinda aquí:

  1. Varios PDF se unen y el resultado conserva todas las páginas.
  2. Una imagen (la firma del canvas HTML5) se convierte a página PDF.
  3. Un anexo corrupto NO tumba el consolidado: se omite con aviso.

Todo el contenido de prueba se genera al vuelo — el repo es público y no
se versionan documentos de organizaciones reales.
"""
import io
import unittest

from apps.documentos.services.pdf_consolidado import Anexo, consolidar, imagen_a_pdf


def _pdf(paginas: int = 1, texto: str = "anexo") -> bytes:
    from reportlab.pdfgen import canvas as rl_canvas

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf)
    for i in range(paginas):
        c.drawString(100, 700, f"{texto} {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def _png() -> bytes:
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _paginas(pdf_bytes: bytes) -> int:
    from PyPDF2 import PdfReader
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


class ConsolidarTests(unittest.TestCase):
    def test_une_varios_pdf_conservando_paginas(self):
        anexos = [
            Anexo("Soporte legal", _pdf(2)),
            Anexo("Cédula", _pdf(1)),
            Anexo("RUT", _pdf(3)),
        ]
        salida = consolidar(anexos, titulo="Propuesta X", portada=False)
        self.assertIsNotNone(salida)
        self.assertEqual(_paginas(salida), 6)
        self.assertTrue(salida.startswith(b"%PDF"))

    def test_portada_agrega_una_pagina(self):
        anexos = [Anexo("Soporte legal", _pdf(1))]
        con = consolidar(anexos, titulo="Propuesta X", subtitulos=["NIT 900123456"])
        sin = consolidar(anexos, titulo="Propuesta X", portada=False)
        self.assertEqual(_paginas(con), _paginas(sin) + 1)

    def test_imagen_se_convierte_en_pagina(self):
        salida = consolidar([Anexo("Firma", _png(), "image/png")], portada=False)
        self.assertEqual(_paginas(salida), 1)

    def test_imagen_a_pdf_devuelve_pdf(self):
        pdf = imagen_a_pdf(Anexo("Firma", _png(), "image/png"))
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_imagen_corrupta_no_lanza(self):
        self.assertIsNone(imagen_a_pdf(Anexo("Firma", b"no soy una imagen", "image/png")))

    def test_anexo_corrupto_se_omite_con_aviso(self):
        # 2 páginas buenas + 1 página de aviso por el anexo roto.
        anexos = [Anexo("Bueno", _pdf(2)), Anexo("Roto", b"basura", "application/pdf")]
        salida = consolidar(anexos, portada=False)
        self.assertEqual(_paginas(salida), 3)

    def test_sin_anexos_devuelve_none(self):
        self.assertIsNone(consolidar([]))
        self.assertIsNone(consolidar([Anexo("Vacío", b"")]))

    def test_mime_desconocido_se_intenta_como_pdf(self):
        # El navegador manda a veces application/octet-stream para un PDF.
        salida = consolidar(
            [Anexo("Soporte", _pdf(1), "application/octet-stream")], portada=False)
        self.assertEqual(_paginas(salida), 1)


if __name__ == "__main__":
    unittest.main()
