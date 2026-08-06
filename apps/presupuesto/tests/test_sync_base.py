# -*- coding: utf-8 -*-
"""C3 — helper `SyncOficialCommand` (base de los comandos de sync).

Prueba el mecanismo del upsert unificado SIN tocar la BD: se simula el cursor y
se captura el SQL que se le pasaría a `execute_values`. Así se verifica que el
INSERT ... ON CONFLICT ... DO UPDATE sale bien armado y que las columnas espejo
(synced_at, fuente, hash_fila, fecha_fuente) se inyectan en el orden correcto,
antes de cablear el helper a ningún comando de producción.
"""
import unittest
from unittest import mock

from core.sync_oficial import SyncOficialCommand


class HashFilaTests(unittest.TestCase):
    def setUp(self):
        self.h = SyncOficialCommand.hash_fila

    def test_determinista(self):
        self.assertEqual(self.h({"a": 1, "b": 2}), self.h({"a": 1, "b": 2}))

    def test_orden_de_claves_no_importa(self):
        self.assertEqual(self.h({"a": 1, "b": 2}), self.h({"b": 2, "a": 1}))

    def test_cambia_si_cambia_el_dato(self):
        self.assertNotEqual(self.h({"a": 1}), self.h({"a": 2}))

    def test_es_sha256(self):
        self.assertEqual(len(self.h({"x": 1})), 64)


class UpsertSQLTests(unittest.TestCase):
    """Se captura el SQL y los valores que recibiría execute_values."""

    def _upsert(self, **kw):
        cmd = SyncOficialCommand()
        cur = mock.MagicMock()
        with mock.patch("core.sync_oficial.execute_values") as ev:
            n = cmd.upsert(cur, **kw)
        # execute_values(cursor, sql, valores)
        if ev.called:
            _cur, sql, valores = ev.call_args.args
        else:
            sql, valores = None, None
        return n, sql, valores

    def test_estructura_basica(self):
        n, sql, valores = self._upsert(
            tabla="cai", clave="id", columnas=["id", "nombre"],
            filas=[{"id": 1, "nombre": "CAI Norte"}], fuente="SCJ",
        )
        self.assertEqual(n, 1)
        # columnas de datos + espejo, en orden
        self.assertIn("INSERT INTO cai (id, nombre, synced_at, fuente, hash_fila) VALUES %s", sql)
        self.assertIn("ON CONFLICT (id) DO UPDATE SET", sql)
        # la clave NO se actualiza; el resto sí
        self.assertNotIn("id = EXCLUDED.id", sql)
        for c in ("nombre", "synced_at", "fuente", "hash_fila"):
            self.assertIn(f"{c} = EXCLUDED.{c}", sql)
        # la fila tiene: id, nombre, synced_at, fuente, hash_fila = 5 valores
        self.assertEqual(len(valores[0]), 5)
        self.assertEqual(valores[0][3], "SCJ")            # fuente
        self.assertEqual(len(valores[0][4]), 64)          # hash_fila (sha256)

    def test_where_del_do_update_se_respeta(self):
        """El guardia que impide pisar filas que no son de la fuente.

        `sync_cai` lo necesita: los CAI móviles los carga Seguridad a mano con
        `fuente='MANUAL'`, y sin este WHERE la corrida siguiente del sync los
        convertiría en fijos. Es una pérdida de datos que **no da ningún
        error** — por eso está fijada en un test y no solo en un comentario.
        """
        _n, sql, _v = self._upsert(
            tabla="cai", clave="codigo", columnas=["codigo", "nombre"],
            filas=[{"codigo": "C1", "nombre": "CAI Sur"}], fuente="SCJ",
            where="cai.fuente = 'SCJ'",
        )
        self.assertTrue(sql.rstrip().endswith("WHERE cai.fuente = 'SCJ'"), sql)
        # y el WHERE va DESPUÉS del SET, no en medio
        self.assertLess(sql.index("DO UPDATE SET"), sql.index("WHERE cai.fuente"))

    def test_sin_where_no_se_agrega_clausula(self):
        _n, sql, _v = self._upsert(
            tabla="t", clave="id", columnas=["id", "x"],
            filas=[{"id": 1, "x": 2}], con_hash=False,
        )
        self.assertNotIn("WHERE", sql)

    def test_clave_compuesta(self):
        _n, sql, _v = self._upsert(
            tabla="puente", clave=["a", "b"], columnas=["a", "b", "v"],
            filas=[{"a": 1, "b": 2, "v": 9}], con_hash=False,
        )
        self.assertIn("ON CONFLICT (a, b) DO UPDATE SET", sql)
        self.assertNotIn("a = EXCLUDED.a", sql)
        self.assertNotIn("b = EXCLUDED.b", sql)
        self.assertIn("v = EXCLUDED.v", sql)

    def test_sin_hash_ni_fuente_solo_synced_at(self):
        _n, sql, valores = self._upsert(
            tabla="t", clave="id", columnas=["id", "x"],
            filas=[{"id": 1, "x": 5}], con_hash=False,
        )
        self.assertIn("INSERT INTO t (id, x, synced_at) VALUES %s", sql)
        self.assertEqual(len(valores[0]), 3)   # id, x, synced_at

    def test_fecha_fuente_se_inyecta(self):
        _n, sql, valores = self._upsert(
            tabla="t", clave="id", columnas=["id"], filas=[{"id": 1}],
            fecha_fuente="2026-01-01", con_hash=False,
        )
        self.assertIn("fecha_fuente", sql)
        self.assertEqual(valores[0][-1], "2026-01-01")

    def test_reproduce_el_upsert_de_placas(self):
        # sync_placas ya usa este patrón a mano; el helper debe generar el MISMO
        # SQL, para poder migrarlo sin cambiar comportamiento.
        _n, sql, _v = self._upsert(
            tabla="placa_domiciliaria", clave="objectid",
            columnas=["objectid", "via", "placa", "lon", "lat", "en_kennedy"],
            filas=[{"objectid": 1, "via": "x", "placa": "y", "lon": 1.0,
                    "lat": 2.0, "en_kennedy": True}],
            con_hash=False,
        )
        self.assertIn(
            "INSERT INTO placa_domiciliaria (objectid, via, placa, lon, lat, "
            "en_kennedy, synced_at) VALUES %s", sql)
        self.assertIn("ON CONFLICT (objectid) DO UPDATE SET", sql)
        self.assertIn("synced_at = EXCLUDED.synced_at", sql)

    def test_filas_vacias_no_llama_execute_values(self):
        n, sql, _v = self._upsert(tabla="t", clave="id", columnas=["id"], filas=[])
        self.assertEqual(n, 0)
        self.assertIsNone(sql)
