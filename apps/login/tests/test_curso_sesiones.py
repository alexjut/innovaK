"""Smoke tests del PR-A módulo Curso Docente.

Verifica que los 8 modelos sobre tablas pre-existentes en BD
(`clase`, `horario_clase`, `asistencia_clase`, `evaluacion_participante`,
`docente`, `grupo`, `acudiente`, `nota_medica`) cargan, tienen el
`db_table` correcto y que las 4 nuevas secuencias funcionan
(DEFAULT nextval aplicado en PR-A DDL).
"""
import unittest


class ModelosCursoSesionesTests(unittest.TestCase):
    """Los 8 modelos del módulo Curso Docente cargan y mapean a sus tablas."""

    def test_clase_importable(self):
        from apps.login.models.curso_sesiones import Clase
        self.assertEqual(Clase._meta.db_table, 'clase')
        # Tabla viva (puede estar vacía hoy)
        self.assertGreaterEqual(Clase.objects.count(), 0)

    def test_horario_clase_importable(self):
        from apps.login.models.curso_sesiones import HorarioClase
        self.assertEqual(HorarioClase._meta.db_table, 'horario_clase')
        self.assertGreaterEqual(HorarioClase.objects.count(), 0)

    def test_asistencia_clase_importable(self):
        from apps.login.models.curso_sesiones import AsistenciaClase
        self.assertEqual(AsistenciaClase._meta.db_table, 'asistencia_clase')
        self.assertGreaterEqual(AsistenciaClase.objects.count(), 0)

    def test_evaluacion_participante_importable(self):
        from apps.login.models.curso_sesiones import EvaluacionParticipante
        self.assertEqual(EvaluacionParticipante._meta.db_table, 'evaluacion_participante')
        self.assertGreaterEqual(EvaluacionParticipante.objects.count(), 0)

    def test_docente_importable(self):
        from apps.login.models.curso_sesiones import Docente
        self.assertEqual(Docente._meta.db_table, 'docente')
        self.assertGreaterEqual(Docente.objects.count(), 0)

    def test_grupo_importable(self):
        from apps.login.models.curso_sesiones import Grupo
        self.assertEqual(Grupo._meta.db_table, 'grupo')

    def test_acudiente_importable(self):
        from apps.login.models.curso_sesiones import Acudiente
        self.assertEqual(Acudiente._meta.db_table, 'acudiente')

    def test_nota_medica_importable(self):
        from apps.login.models.curso_sesiones import NotaMedica
        self.assertEqual(NotaMedica._meta.db_table, 'nota_medica')


class SecuenciasInstaladasTests(unittest.TestCase):
    """El DDL 005 dejó secuencias propias en las 4 tablas que las necesitaban."""

    def _seq_for(self, tabla):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("SELECT pg_get_serial_sequence(%s, 'id')", [tabla])
            return c.fetchone()[0]

    def test_clase_tiene_secuencia(self):
        self.assertEqual(self._seq_for('clase'), 'public.clase_id_seq')

    def test_horario_clase_tiene_secuencia(self):
        self.assertEqual(self._seq_for('horario_clase'), 'public.horario_clase_id_seq')

    def test_asistencia_clase_tiene_secuencia(self):
        self.assertEqual(self._seq_for('asistencia_clase'), 'public.asistencia_clase_id_seq')

    def test_grupo_tiene_secuencia(self):
        self.assertEqual(self._seq_for('grupo'), 'public.grupo_id_seq')


class IndicesYConstraintsTests(unittest.TestCase):
    """El DDL 005 creó el UNIQUE de asistencia y los índices de lectura."""

    def _indices_de(self, tabla):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = %s
            """, [tabla])
            return {r[0] for r in c.fetchall()}

    def test_unique_asistencia(self):
        idx = self._indices_de('asistencia_clase')
        self.assertIn('ux_asistencia_clase_participante_fecha', idx)

    def test_index_clase_evento(self):
        self.assertIn('ix_clase_evento', self._indices_de('clase'))

    def test_index_asistencia_fecha(self):
        self.assertIn('ix_asistencia_clase_fecha', self._indices_de('asistencia_clase'))
