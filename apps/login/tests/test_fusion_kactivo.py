"""Smoke tests del PR-2 de la fusión kactivo→Evento.

Verifica que los modelos movidos (TipoArchivo, DocumentoEvento,
ParticipanteEvento) viven ahora en apps.login y siguen funcionando
contra las mismas tablas BD (managed=False, mismo db_table).
"""
import unittest


class ModelosMovidosTests(unittest.TestCase):
    """Los modelos antes en apps.kactivo ahora viven en apps.login."""

    def test_tipo_archivo_importable_desde_login(self):
        from apps.login.models.documentos_evento import TipoArchivo
        # Tabla viva: tipo_archivo (1 fila al 2026-05-27).
        self.assertGreaterEqual(TipoArchivo.objects.count(), 0)

    def test_documento_evento_importable_desde_login(self):
        from apps.login.models.documentos_evento import DocumentoEvento
        # Tabla viva: documento_evento (2 filas al 2026-05-27).
        self.assertGreaterEqual(DocumentoEvento.objects.count(), 0)

    def test_participante_evento_importable_desde_login(self):
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        # Tabla viva: participante_evento (~2545 filas al 2026-05-27).
        # Sanity check: la tabla NO se renombró ni se vació.
        self.assertGreater(ParticipanteEvento.objects.count(), 1000)

    def test_modelos_disponibles_en_login_models_init(self):
        # Exposed en apps.login.models para usos cross-app.
        from apps.login.models import (
            TipoArchivo, DocumentoEvento, ParticipanteEvento,
        )
        self.assertTrue(hasattr(TipoArchivo, '_meta'))
        self.assertTrue(hasattr(DocumentoEvento, '_meta'))
        self.assertTrue(hasattr(ParticipanteEvento, '_meta'))


class TablasMantienenNombre(unittest.TestCase):
    """db_table NO cambió — datos preservados."""

    def test_tipo_archivo_db_table(self):
        from apps.login.models.documentos_evento import TipoArchivo
        self.assertEqual(TipoArchivo._meta.db_table, 'tipo_archivo')

    def test_documento_evento_db_table(self):
        from apps.login.models.documentos_evento import DocumentoEvento
        self.assertEqual(DocumentoEvento._meta.db_table, 'documento_evento')

    def test_participante_evento_db_table(self):
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        self.assertEqual(ParticipanteEvento._meta.db_table, 'participante_evento')


class InscripcionFKResuelta(unittest.TestCase):
    """FK 'kactivo.Curso' en Inscripcion ya es IntegerField plano (decisión #3 B)."""

    def test_inscripcion_curso_id_es_integer(self):
        from django.db import models as dj_models
        from apps.login.models.inscripcion import Inscripcion
        campo = Inscripcion._meta.get_field('curso_id')
        self.assertIsInstance(campo, dj_models.IntegerField)
        # Asegura que el column SQL sigue siendo curso_id (preserva datos).
        self.assertEqual(campo.db_column, 'curso_id')


class InfoTerrenoImportsActualizados(unittest.TestCase):
    """info_terreno.py importa desde login, no desde kactivo."""

    def test_info_terreno_modulo_carga(self):
        # Si los imports rotos al borrar kactivo, este import lanzaría.
        from apps.login.views.eventos import info_terreno
        self.assertTrue(hasattr(info_terreno, 'confirmar_llegada_info_terreno'))
        self.assertTrue(hasattr(info_terreno, 'info_terreno_exitoso'))
