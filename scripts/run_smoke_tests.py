#!/usr/bin/env python
"""
Runner de smoke tests innovaK.

NO usa `manage.py test` para evitar que Django intente crear BD test
(la BD es externa, managed=False, compartida; crear BD test fallaría).

Bypass: hace `django.setup()` y descubre tests con unittest discover.
Los tests son `unittest.TestCase` puros (no `django.test.TestCase`)
y usan Test Client + force_login del primer superuser existente.

Solo hace GETs (read-only) — seguro contra la BD de producción.

Uso:
    docker exec innova_k python scripts/run_smoke_tests.py [-v]
"""
import os
import sys
import unittest

# Asegura que el cwd del proyecto esté en sys.path antes de django.setup()
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
# Cierre Etapa C #3: el rate limit usa key=ip; los tests todos disparan
# desde testserver, así que saturan en segundos. Desactivamos aquí.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
django.setup()


def main():
    verbosity = 2 if "-v" in sys.argv or "--verbose" in sys.argv else 1
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for module_name in [
        "apps.dashboard.tests.test_smoke",
        "apps.login.tests.test_smoke",
        "apps.login.tests.test_permisos",
        "apps.login.tests.test_rbac_pr0",
        "apps.login.tests.test_rbac_pr1",
        "apps.login.tests.test_rbac_pr2_pr3",
        "apps.login.tests.test_rbac_pr4_scope",
        "apps.login.tests.test_rbac_pr6_auditoria",
        "apps.login.tests.test_rbac_pr5a_accesos",
        "apps.login.tests.test_rbac_b0_roles",
        "apps.login.tests.test_rbac_prc0_coordinador",
        "apps.login.tests.test_rbac_pra_crear_actividad",
        "apps.login.tests.test_rbac_b1_scope_contrato",
        "apps.login.tests.test_rbac_b2_scope_curso",
        "apps.login.tests.test_rbac_b3_panel_subgrupo",
        "apps.login.tests.test_rbac_dashboard_ia_scope",
        "apps.login.tests.test_rbac_bdeuda1_miscursos",
        "apps.login.tests.test_jwt",
        "apps.login.tests.test_fusion_kactivo",
        "apps.login.tests.test_api_inscripcion",
        "apps.login.tests.test_openapi_schema",
        "apps.login.tests.test_jwt_optional",
        "apps.login.tests.test_e2e_flujos",
        "apps.login.tests.test_etapa_c_cierre",
        "apps.login.tests.test_curso_sesiones",
        "apps.login.tests.test_curso_docente",
        "apps.login.tests.test_curso_notas",
        "apps.login.tests.test_curso_reporte",
        "apps.login.tests.test_captura_generica",
        "apps.login.tests.test_actividades_sector",
        "apps.login.tests.test_qa_fase1",
        "apps.login.tests.test_evento_ubicacion",
        "apps.presupuesto.tests.test_smoke",
        "apps.presupuesto.tests.test_api",
        "apps.presupuesto.tests.test_contratos_infra",
        "apps.presupuesto.tests.test_saldos",
        "apps.presupuesto.tests.test_sync_orquestador",
        "apps.presupuesto.tests.test_sync_base",
        "apps.presupuesto.tests.test_panel_area",
        "apps.presupuesto.tests.test_marcador_avance",
        "apps.presupuesto.tests.test_muro_subgrupos",
        "apps.presupuesto.tests.test_expediente_proyecto",
        "apps.presupuesto.tests.test_expediente_contrato",
        "apps.presupuesto.tests.test_completitud_expediente",
        "apps.presupuesto.tests.test_scope_escritura",
        "apps.jovenes_a_la_e.tests.test_cargue_excel",
        "apps.jovenes_a_la_e.tests.test_cargue_servicio",
        "apps.banco_iniciativas.tests.test_smoke",
        "apps.banco_iniciativas.tests.test_api",
        "apps.banco_iniciativas.tests.test_puntaje",
        "apps.banco_iniciativas.tests.test_asignar_estrato_org",
        "apps.banco_iniciativas.tests.test_bono_estrato",
        "apps.banco_iniciativas.tests.test_matriz_oficial",
        "apps.banco_iniciativas.tests.test_ranking_oficial",
        "apps.banco_iniciativas.tests.test_borrador",
        "apps.banco_iniciativas.tests.test_form_documento_maestro",
        "apps.login.tests.test_consulta_publica",
        "apps.caracterizacion.tests.test_smoke",
        "apps.caracterizacion.tests.test_api",
        "apps.caracterizacion.tests.test_internal",
        "apps.georeferenciacion.tests.test_smoke",
        "apps.georeferenciacion.tests.test_estratificacion",
        "apps.georeferenciacion.tests.test_capa_barrios",
        "apps.georeferenciacion.tests.test_geocoder",
        "apps.georeferenciacion.tests.test_capas",
        "apps.georeferenciacion.tests.test_censo_escuelas",
        "apps.georeferenciacion.tests.test_diagnostico",
        "apps.georeferenciacion.tests.test_resolver_territorio",
        "apps.documentos.tests.test_smoke",
        "apps.documentos.tests.test_cifrado",
        "apps.documentos.tests.test_pdf_consolidado",
        "apps.documentos.tests.test_onedrive_storage",
        "apps.jovenes_a_la_e.tests.test_smoke",
        "apps.jovenes_a_la_e.tests.test_api",
        "apps.festivales.tests.test_smoke",
        "apps.festivales.tests.test_api",
        "apps.festivales.tests.test_dia",
        "apps.festivales.tests.test_biblioteca",
        "apps.festivales.tests.test_insights",
        "apps.festivales.tests.test_aforo",
        "apps.festivales.tests.test_publico",
        "apps.festivales.tests.test_percepcion",
        "apps.festivales.tests.test_evaluacion",
        "apps.educacion.tests.test_smoke",
        "apps.educacion.tests.test_instituciones",
        "apps.onboarding.tests.test_smoke",
        "apps.votaciones.tests.test_api",
        "apps.dashboard.tests.test_api",
        "apps.dashboard.tests.test_cockpit",
    ]:
        suite.addTests(loader.loadTestsFromName(module_name))
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
