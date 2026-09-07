"""La formulación DENTRO del contrato: la mitad que faltaba de la traza.

El expediente ya colgaba las formulaciones de la META, así que se veía «esta
meta tiene la formulación F-001». Lo que no existía era el camino inverso —
«este contrato nació de F-001»— y por eso la cadena Formulación → Contrato →
Etapa → Seguimiento se leía por tramos y nunca de corrido. La tabla puente
llevaba 0 filas con el endpoint para llenarla ya escrito.
"""
import unittest

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.presupuesto.models import Formulacion, FormulacionContrato
from apps.presupuesto.services.completitud_expediente import (
    CAMPOS, completitud_area,
)
from apps.presupuesto.services.formulacion_contrato import (
    EnlaceInvalido, enlazar_a_contrato, formulaciones_de,
)


def _un_caso():
    """(formulación, contrato_id) de la MISMA área, o `None`.

    Se busca en la base en vez de fijar ids: los que había el 2026-09-07
    (F-098 con el contrato 77 de Cultura) pueden moverse, y un test que se cae
    porque cambió un id no denuncia nada.
    """
    for f in Formulacion.objects.exclude(subgrupo_id=None):
        datos = completitud_area(f.subgrupo_id)
        for p in datos.get("proyectos", []):
            for c in p["contratos"]:
                if not FormulacionContrato.objects.filter(
                        contrato_id=c["contrato_id"]).exists():
                    return f, c["contrato_id"]
    return None


class CampoFormulacionTests(unittest.TestCase):

    def test_el_campo_existe_y_vive_en_relaciones(self):
        """Va con proyecto y actividad: los tres dicen a qué se ata el
        contrato, y ninguno viene de fuente oficial."""
        campo = next((c for c in CAMPOS if c[0] == "formulacion"), None)
        self.assertIsNotNone(campo, "el campo no está declarado")
        clave, bloque, etiqueta, fuente, editable = campo
        self.assertEqual(bloque, "relaciones")
        self.assertIsNone(fuente, "ninguna fuente oficial publica esto")
        self.assertTrue(editable, "el área tiene que poder engancharlo")

    def test_el_campo_llega_a_la_ficha_del_contrato(self):
        """Declararlo en `CAMPOS` no basta: tiene que llegar a la ficha, que es
        lo que la pantalla pinta.

        Se recorren TODAS las áreas con formulación y no solo la primera: con
        `[:1]` el test se saltaba solo cuando esa área no tenía contratos
        cargados, y un skip por accidente se lee igual que «no aplica».
        """
        for sg in (Formulacion.objects.exclude(subgrupo_id=None)
                   .values_list("subgrupo_id", flat=True).distinct()):
            for p in completitud_area(sg).get("proyectos", []):
                for c in p["contratos"]:
                    self.assertIn("formulacion", {x["clave"] for x in c["campos"]})
                    return
        self.skipTest("Ningún área con formulación tiene contratos cargados.")


class EnlaceTests(unittest.TestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.filter(is_superuser=True).first()
        if self.usuario is None:
            self.skipTest("No hay superusuario para firmar el enlace.")
        self.caso = _un_caso()
        if self.caso is None:
            self.skipTest("No hay una formulación y un contrato de la misma área.")

    def test_enlazar_completa_el_campo_y_sube_la_completitud(self):
        f, cid = self.caso
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                antes = self._ficha(f.subgrupo_id, cid)
                self.assertEqual(
                    next(x for x in antes["campos"] if x["clave"] == "formulacion")["estado"],
                    "sin_dato")

                enlazar_a_contrato(f, cid, self.usuario)

                despues = self._ficha(f.subgrupo_id, cid)
                campo = next(x for x in despues["campos"] if x["clave"] == "formulacion")
                self.assertEqual(campo["estado"], "ok")
                self.assertEqual(campo["valor"][0]["formulacion_id"], f.id)
                self.assertEqual(despues["completos"], antes["completos"] + 1,
                                 "el enlace no movió la completitud")
                raise RuntimeError("revertir")

    def test_la_traza_se_lee_en_los_dos_sentidos(self):
        """Desde la formulación ya se veía; desde el contrato es lo nuevo."""
        f, cid = self.caso
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.assertEqual(formulaciones_de(cid), [])
                enlazar_a_contrato(f, cid, self.usuario)
                salida = formulaciones_de(cid)
                self.assertEqual(len(salida), 1)
                self.assertEqual(salida[0]["formulacion_id"], f.id)
                self.assertEqual(salida[0]["codigo"], f"F-{f.id:03d}")
                raise RuntimeError("revertir")

    def test_no_se_enlaza_dos_veces(self):
        f, cid = self.caso
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                enlazar_a_contrato(f, cid, self.usuario)
                with self.assertRaises(EnlaceInvalido):
                    enlazar_a_contrato(f, cid, self.usuario)
                raise RuntimeError("revertir")

    def test_no_se_enlaza_la_formulacion_de_otra_area(self):
        """El scope de la vista cuida el contrato; esto cuida el otro extremo.
        Sin los dos, un área podría colgarle su formulación al contrato ajeno y
        la traza diría una cosa falsa en la pantalla del vecino."""
        f, cid = self.caso
        ajena = Formulacion.objects.exclude(subgrupo_id=f.subgrupo_id).exclude(
            subgrupo_id=None).first()
        if ajena is None:
            self.skipTest("No hay formulaciones de dos áreas distintas.")
        with self.assertRaises(EnlaceInvalido):
            enlazar_a_contrato(ajena, cid, self.usuario)

    def test_un_contrato_que_no_existe_no_se_inventa(self):
        """Crear un contrato desde el expediente de otro contrato dejaría una
        fila inventada donde debería haber un aviso."""
        f, _ = self.caso
        with self.assertRaises(EnlaceInvalido):
            enlazar_a_contrato(f, 99999999, self.usuario)

    def _ficha(self, subgrupo_id, contrato_id):
        datos = completitud_area(subgrupo_id)
        return next(c for p in datos["proyectos"] for c in p["contratos"]
                    if c["contrato_id"] == contrato_id)
