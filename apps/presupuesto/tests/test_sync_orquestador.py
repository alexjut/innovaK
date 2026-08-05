# -*- coding: utf-8 -*-
"""C4 (2026-08-05) — orquestador de fuentes oficiales.

Antes cubría 2 de 11 fuentes y ESCRIBÍA sin pedir permiso (los ingest escriben
por defecto y el orquestador los llamaba sin flags). Ahora:
  - cubre las 11 fuentes de RUMBO §1.1 (10 invocaciones; Colegios trae 2),
  - es SECO por defecto; solo escribe con --write,
  - traduce por convención el modo de cada comando al flag que ese comando
    entiende (unos usan --write, otros --dry-run, uno no tiene modo seco),
  - salta las pesadas (placas: 1,77M filas) salvo --incluir-pesadas.

Se prueba SIN correr los comandos reales (que pegan a servicios externos y a la
BD): se simula `call_command` y se verifica qué flags recibió cada fuente. El
riesgo que estos tests cazan es el de mapear mal un flag y escribir sin querer
—o no escribir cuando debía—, que es justo lo peligroso de un cron.
"""
import unittest
from unittest import mock

from django.core.management import call_command

from apps.presupuesto.management.commands import sync_fuentes_oficiales as mod


class KwargsPorModoTests(unittest.TestCase):
    """El traductor modo→flags, aislado."""

    def test_seco(self):
        self.assertEqual(mod.kwargs_por_modo("seco", write=True), ({"write": True}, True))
        self.assertEqual(mod.kwargs_por_modo("seco", write=False), ({}, True))

    def test_escribe(self):
        # Escribe por defecto → en seco hay que FRENARLO con dry_run=True.
        self.assertEqual(mod.kwargs_por_modo("escribe", write=True), ({}, True))
        self.assertEqual(mod.kwargs_por_modo("escribe", write=False), ({"dry_run": True}, True))

    def test_solo_write_se_salta_en_seco(self):
        self.assertEqual(mod.kwargs_por_modo("solo_write", write=True), ({}, True))
        self.assertEqual(mod.kwargs_por_modo("solo_write", write=False), ({}, False))

    def test_solo_lectura_corre_siempre(self):
        self.assertEqual(mod.kwargs_por_modo("solo_lectura", write=True), ({}, True))
        self.assertEqual(mod.kwargs_por_modo("solo_lectura", write=False), ({}, True))


class FuentesConfigTests(unittest.TestCase):
    def test_cubre_diez_invocaciones(self):
        self.assertEqual(len(mod.FUENTES), 10)

    def test_estratificacion_va_por_sync_capa_no_por_el_bespoke(self):
        # El caso peligroso: manzana_estrato la escribían dos comandos con
        # defaults opuestos. El orquestador usa SOLO sync_capa (seco por defecto).
        comandos = [c for _, c, *_ in mod.FUENTES]
        self.assertIn("sync_capa", comandos)
        self.assertNotIn("sync_estratificacion", comandos)

    def test_placas_esta_marcada_pesada(self):
        placas = [f for f in mod.FUENTES if f[1] == "sync_placas"]
        self.assertEqual(len(placas), 1)
        self.assertTrue(placas[0][4], "sync_placas debe estar marcada pesada")


class OrquestadorHandleTests(unittest.TestCase):
    """handle() con call_command simulado: qué recibe cada fuente."""

    def _correr(self, **opts):
        with mock.patch.object(mod.Command, "_abrir_log", return_value=None), \
             mock.patch.object(mod, "call_command") as cc:
            call_command("sync_fuentes_oficiales", **opts)
        llamadas = {}
        for c in cc.call_args_list:
            cmd = c.args[0]
            pos = c.args[1:]
            clave = cmd + (":" + str(pos[0]) if pos else "")
            llamadas[clave] = c.kwargs
        return llamadas

    def test_seco_no_pasa_write_y_frena_los_que_escriben(self):
        ll = self._correr()  # sin --write
        # sync_capa (seco) → sin write
        self.assertEqual(ll["sync_capa:estratificacion"], {})
        self.assertEqual(ll["sync_capa:sector_catastral"], {})
        self.assertEqual(ll["sync_capa:barrios_legalizados"], {})
        # Tras C3 Paso 2 TODOS son seco por defecto: en seco no reciben flag.
        self.assertEqual(ll["sync_colegios"], {})
        self.assertEqual(ll["sync_cai"], {})
        self.assertEqual(ll["ingest_sdp_datos_abiertos"], {})
        self.assertEqual(ll["ingest_secop_contratos"], {})
        # solo_lectura corre; solo_write se salta; pesada se salta
        self.assertIn("sdp_preview", ll)
        self.assertNotIn("resolver_geometria_tramos", ll)
        self.assertNotIn("sync_placas", ll)

    def test_write_escribe_y_no_frena(self):
        ll = self._correr(write=True)
        self.assertEqual(ll["sync_capa:estratificacion"], {"write": True})
        self.assertEqual(ll["sync_colegios"], {"write": True})
        self.assertEqual(ll["ingest_sdp_datos_abiertos"], {"write": True})
        # solo_write ahora sí corre; pesada sigue saltada
        self.assertIn("resolver_geometria_tramos", ll)
        self.assertNotIn("sync_placas", ll)

    def test_desde_anio_solo_a_secop(self):
        ll = self._correr(write=True, desde_anio=2024)
        self.assertEqual(ll["ingest_secop_contratos"], {"write": True, "desde_anio": 2024})
        self.assertEqual(ll["ingest_sdp_datos_abiertos"], {"write": True})  # SDP no recibe desde_anio

    def test_incluir_pesadas_corre_placas(self):
        ll = self._correr(write=True, incluir_pesadas=True)
        self.assertEqual(ll["sync_placas"], {"write": True})
