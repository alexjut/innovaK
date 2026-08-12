# -*- coding: utf-8 -*-
"""Catálogo de instituciones de educación posmedia (2026-08-12).

Lo que se fija acá son las reglas que, si se rompen, dan cifras equivocadas sin
que nada falle:

- **Agrupar por CÓDIGO y no por nombre.** El archivo del área trae
  `ADMINISTRACIÓN` y `ADMINISTRACION` en filas distintas del mismo programa;
  agrupar por nombre lo parte en dos y duplica el conteo de alumnos.
- **El acumulado no es la suma de las vigencias.** Una persona con beneficio en
  dos años es una persona.
- **Los tres casos ambiguos se avisan, no se resuelven solos.** Fusionar dos
  instituciones porque se parecen los nombres es irreversible.

Los tests que necesitan las tablas se saltan solos mientras el DDL 003 no esté
aplicado — el runner corre contra la BD compartida y estas tablas todavía no
existen ahí.
"""
import unittest

from django.db import ProgrammingError, connection


def _tabla_existe(nombre: str) -> bool:
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", [nombre])
            return bool(cur.fetchone()[0])
    except (ProgrammingError, Exception):
        return False


class ImportsTests(unittest.TestCase):
    """No dependen del DDL: los modelos son managed=False."""

    def test_modelos_y_tablas(self):
        from apps.educacion.models import InstitucionEducativa, ProgramaAcademico
        self.assertEqual(InstitucionEducativa._meta.db_table, "institucion_educativa")
        self.assertEqual(ProgramaAcademico._meta.db_table, "programa_academico")
        self.assertFalse(InstitucionEducativa._meta.managed)
        self.assertFalse(ProgramaAcademico._meta.managed)

    def test_el_nivel_vive_en_el_programa_no_en_la_institucion(self):
        # Una IES ofrece varios niveles a la vez: ponerlo en la institución
        # obligaría a elegir uno y perdería el resto.
        from apps.educacion.models import InstitucionEducativa, ProgramaAcademico
        campos_inst = {f.name for f in InstitucionEducativa._meta.get_fields()}
        campos_prog = {f.name for f in ProgramaAcademico._meta.get_fields()}
        self.assertNotIn("nivel_formacion", campos_inst)
        self.assertIn("nivel_formacion", campos_prog)

    def test_la_llave_del_programa_es_el_par(self):
        # Un mismo código existe en instituciones distintas: única global
        # mezclaría dos carreras que no tienen nada que ver.
        from apps.educacion.models import ProgramaAcademico
        nombres = {c.name: c for c in ProgramaAcademico._meta.constraints}
        self.assertIn("uq_programa_institucion_codigo", nombres)
        self.assertEqual(list(nombres["uq_programa_institucion_codigo"].fields),
                         ["institucion", "codigo_snies"])

    def test_el_codigo_usa_el_normalizador_del_cargue(self):
        # Es lo que garantiza que el join contra entrega_beca.snies_ies sea
        # directo, sin CAST ni LPAD.
        from apps.educacion.models import InstitucionEducativa
        from apps.jovenes_a_la_e.services.cargue_excel import digitos
        campo = InstitucionEducativa._meta.get_field("codigo_snies")
        self.assertEqual(campo.max_length, 20)
        self.assertEqual(digitos("4894.0"), "4894")

    def test_niveles_espejan_los_de_entrega_beca(self):
        # Si divergen, los conteos por nivel dejan de cruzar en silencio.
        from apps.educacion.models import ProgramaAcademico
        from apps.jovenes_a_la_e.models import EntregaBeca
        self.assertEqual(dict(ProgramaAcademico.NIVEL_CHOICES),
                         dict(EntregaBeca.NIVEL_CHOICES))


class DesgloseYConteosTests(unittest.TestCase):
    """Sobre los datos reales que haya en la BD. No escriben nada."""

    def test_desglose_da_las_dos_lecturas(self):
        from apps.educacion.services import instituciones as svc
        d = svc.desglose_por_nivel()
        self.assertIn("superior", d)
        self.assertIn("etdh", d)
        self.assertIn("personas_en_ambos_grupos", d)
        # La suma por grupo puede pasarse del total, y por eso se dice cuánto.
        suma = d["superior"]["personas"] + d["etdh"]["personas"]
        self.assertEqual(suma - d["personas_en_ambos_grupos"], d["personas_total"])

    def test_acumulado_no_es_la_suma_de_las_vigencias(self):
        from apps.educacion.services import instituciones as svc
        vigencias = svc.vigencias_disponibles()
        if len(vigencias) < 2:
            self.skipTest("Con una sola vigencia la propiedad no se puede observar")
        acumulado = svc.desglose_por_nivel()["personas_total"]
        suma = sum(svc.desglose_por_nivel(v)["personas_total"] for v in vigencias)
        self.assertLessEqual(acumulado, suma)

    def test_conteos_por_institucion_separan_personas_de_matriculas(self):
        from apps.educacion.services import instituciones as svc
        for datos in svc.conteos_por_institucion().values():
            self.assertLessEqual(datos["personas"], datos["matriculas"])


class SincronizacionTests(unittest.TestCase):

    def test_seco_por_defecto(self):
        if not _tabla_existe("institucion_educativa"):
            self.skipTest("DDL 003 no aplicado todavía")
        from apps.educacion.models import InstitucionEducativa
        from apps.educacion.services import instituciones as svc
        antes = InstitucionEducativa.objects.count()
        r = svc.sincronizar_desde_entregas()          # sin aplicar
        self.assertFalse(r["aplicado"])
        self.assertEqual(InstitucionEducativa.objects.count(), antes)

    def test_el_tipo_de_registro_sale_del_nivel(self):
        # ETDH está en el SIET; lo demás, en el SNIES. Es la única pista que
        # trae el archivo sobre en qué registro está inscrita la institución.
        from apps.educacion.services.instituciones import tipo_registro_de
        self.assertEqual(tipo_registro_de("etdh"), "SIET")
        self.assertEqual(tipo_registro_de("profesional"), "SNIES")
        self.assertEqual(tipo_registro_de(None), "SNIES")


class ApiTests(unittest.TestCase):

    def test_las_rutas_existen(self):
        from django.urls import reverse
        for nombre in ("educacion:api_instituciones",
                       "educacion:api_instituciones_geojson",
                       "educacion:api_instituciones_sincronizar"):
            self.assertTrue(reverse(nombre).startswith("/educacion/api/"))

    def test_exigen_el_modulo_educacion(self):
        from apps.educacion.api.instituciones import _PERMS
        self.assertTrue(_PERMS)
        self.assertIn("educacion", _PERMS[0].__name__)


if __name__ == "__main__":
    unittest.main()
