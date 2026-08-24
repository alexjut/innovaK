"""Auditoría de datos: quién, cuándo, antes, después.

Lo que se protege acá es que el rastro exista y sea legible, y las tres
decisiones que lo hacen usable: que el cero no se confunda con la ausencia, que
un no-cambio no ensucie el historial, y que una auditoría rota nunca tumbe el
dato que ya se guardó.

Estos tests SÍ escriben en `auditoria_dato` — es la única forma de probarlos.
Cada uno limpia lo suyo en `finally`, sin excepción: la BD es compartida y de
producción, y una prueba que deja basura ya nos costó una tarde.
"""
import unittest

from django.contrib.auth import get_user_model

from apps.presupuesto.models.auditoria import AuditoriaDato
from apps.presupuesto.services.auditoria import historial, registrar_cambio

# Entidad falsa a propósito: no colisiona con nada real y hace obvio en la BD
# que una fila con este nombre es de una prueba.
ENTIDAD = "_prueba_auditoria"


class AuditoriaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()

    def _limpiar(self):
        AuditoriaDato.objects.filter(entidad=ENTIDAD).delete()

    # ── el rastro básico ───────────────────────────────────────────────────
    def test_registra_quien_cuando_antes_y_despues(self):
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            fila = registrar_cambio(
                usuario=self.user, entidad=ENTIDAD, entidad_id=1, campo="etapa",
                valor_anterior=None, valor_nuevo="2", observacion="desde la prueba")
            self.assertIsNotNone(fila)
            self.assertEqual(fila.usuario_id, self.user.id)
            self.assertIsNotNone(fila.fecha)
            self.assertEqual(fila.campo, "etapa")
            self.assertIsNone(fila.valor_anterior)
            self.assertEqual(fila.valor_nuevo, "2")
            self.assertEqual(fila.fuente, AuditoriaDato.MANUAL)
        finally:
            self._limpiar()

    def test_congela_el_nombre_del_usuario(self):
        """Si el usuario se borra o se renombra, el rastro sigue diciendo quién fue."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            fila = registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                    entidad_id=2, campo="x", valor_nuevo="1")
            self.assertTrue(fila.usuario_nombre)
        finally:
            self._limpiar()

    # ── las tres decisiones ────────────────────────────────────────────────
    def test_el_cero_no_se_confunde_con_la_ausencia(self):
        """`0` es un dato. `None` es que no había. La auditoría los distingue."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            fila = registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                    entidad_id=3, campo="ejecucion",
                                    valor_anterior=0, valor_nuevo=15)
            self.assertEqual(fila.valor_anterior, "0",
                             "un cero no puede llegar como NULL: diría que estaba vacío")
            self.assertIsNotNone(fila.valor_anterior)
        finally:
            self._limpiar()

    def test_un_no_cambio_no_ensucia_el_historial(self):
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            fila = registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                    entidad_id=4, campo="etapa",
                                    valor_anterior="2", valor_nuevo="2")
            self.assertIsNone(fila)
            self.assertEqual(AuditoriaDato.objects.filter(entidad=ENTIDAD).count(), 0)
        finally:
            self._limpiar()

    def test_una_auditoria_rota_no_tumba_el_dato(self):
        """El dato ya se guardó: reventar acá mostraría un error por algo que sí
        funcionó. Devuelve None y lo deja en el log."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            # `campo` es varchar(60): esto revienta en la BD a propósito.
            fila = registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                    entidad_id=5, campo="x" * 300, valor_nuevo="1")
            self.assertIsNone(fila)
        finally:
            self._limpiar()

    # ── contexto y lectura ─────────────────────────────────────────────────
    def test_deduce_proyecto_y_subgrupo_desde_el_contrato(self):
        """Pasar sólo `contrato_id` basta: el resto lo resuelve el servicio."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        from apps.presupuesto.models.core import ContratoProyecto
        cp = ContratoProyecto.objects.first()
        if cp is None:
            self.skipTest("no hay contratos enganchados a proyecto")
        try:
            fila = registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                    entidad_id=6, campo="etapa", valor_nuevo="3",
                                    contrato_id=cp.contrato_id)
            self.assertEqual(fila.proyecto_id, cp.proyecto_id)
            self.assertIsNotNone(fila.subgrupo_id,
                                 "el subgrupo se deduce del proyecto")
        finally:
            self._limpiar()

    def test_el_historial_sale_del_mas_reciente_al_mas_viejo(self):
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            for v in ("1", "2", "3"):
                registrar_cambio(usuario=self.user, entidad=ENTIDAD,
                                 entidad_id=7, campo="etapa",
                                 valor_anterior=None, valor_nuevo=v)
            h = historial(ENTIDAD, 7)
            self.assertEqual(len(h), 3)
            self.assertEqual([x.valor_nuevo for x in h], ["3", "2", "1"])
        finally:
            self._limpiar()

    def test_la_fuente_distingue_manual_de_oficial(self):
        """Sostiene la precedencia: no es lo mismo que lo escriba una persona
        a que llegue de SECOP."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        try:
            f = registrar_cambio(usuario=self.user, entidad=ENTIDAD, entidad_id=8,
                                 campo="valor", valor_nuevo="100",
                                 fuente=AuditoriaDato.SECOP)
            self.assertEqual(f.fuente, "SECOP")
        finally:
            self._limpiar()
