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
django.setup()


def main():
    verbosity = 2 if "-v" in sys.argv or "--verbose" in sys.argv else 1
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for module_name in [
        "apps.dashboard.tests.test_smoke",
        "apps.login.tests.test_smoke",
        "apps.login.tests.test_permisos",
        "apps.login.tests.test_jwt",
        "apps.presupuesto.tests.test_smoke",
        "apps.banco_iniciativas.tests.test_smoke",
        "apps.caracterizacion.tests.test_smoke",
        "apps.georeferenciacion.tests.test_smoke",
        "apps.documentos.tests.test_smoke",
        "apps.documentos.tests.test_cifrado",
        "apps.jovenes_a_la_e.tests.test_smoke",
    ]:
        suite.addTests(loader.loadTestsFromName(module_name))
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
