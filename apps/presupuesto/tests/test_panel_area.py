"""Tests del panel de ÁREA (la cadena completa por subgrupo).

Lo que se protege acá es la razón de existir del panel nuevo: que un área que
PLANEA y CONTRATA pero todavía no captura eventos deje de verse vacía. El
panel viejo (`panel_subgrupo`) derivaba todo de `evento.subgrupo_id`, y por eso
Educación e Infraestructura salían en blanco teniendo trabajo.

Se apoya en datos reales de `poblacion_kennedy` (BD externa compartida, sin
fixtures — igual que el resto de la suite). Cada test se salta solo si el dato
que necesita no está, en vez de fallar por algo que no es un defecto del
código.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

# Verificados contra la BD el 2026-08-05 (dependencia INVERSIÓN LOCAL = 3).
CULTURA, DEPORTE, EDUCACION, INFRAESTRUCTURA, SEGURIDAD = 1, 2, 8, 37, 38


class PanelAreaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        cls.client_anon = Client(HTTP_HOST=HOST)
        cls.client_auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client_auth.force_login(cls.user)

    def _panel(self, subgrupo_id):
        from apps.presupuesto.services.panel_area import panel_area
        return panel_area(subgrupo_id)

    # ── URL legible ────────────────────────────────────────────────

    def test_los_45_subgrupos_dan_slugs_unicos(self):
        """La URL usa el nombre. Si dos áreas colisionan, una queda inalcanzable."""
        from apps.login.models.funcionario import Subgrupo
        from apps.presupuesto.services.modulos_area import slug_de

        slugs = [slug_de(s) for s in Subgrupo.objects.all()]
        self.assertTrue(all(slugs), "hay un subgrupo cuyo slug queda vacío")
        self.assertEqual(len(slugs), len(set(slugs)), "hay slugs repetidos")

    def test_se_resuelve_por_slug_y_por_id(self):
        """El id sigue sirviendo: un enlace viejo no se puede romper."""
        from apps.presupuesto.services.modulos_area import resolver_area

        self.assertEqual(resolver_area("educacion").id, EDUCACION)
        self.assertEqual(resolver_area(str(EDUCACION)).id, EDUCACION)
        self.assertIsNone(resolver_area("area-que-no-existe"))

    def test_el_panel_devuelve_su_slug(self):
        self.assertEqual(self._panel(SEGURIDAD)["area"]["slug"], "seguridad")

    def test_el_modulo_de_area_apunta_dentro_del_area(self):
        """El CAI es de Seguridad: su tarjeta no puede mandar al mapa general."""
        cai = next(m for m in self._panel(SEGURIDAD)["modulos"]
                   if m["codigo"] == "cai")
        self.assertEqual(cai["ruta"], "/mi-area/seguridad/cai")

    def test_endpoint_acepta_slug(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.client_auth.get("/presupuesto/api/areas/educacion/panel/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["area"]["slug"], "educacion")

    def test_endpoint_con_area_inexistente_da_404(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.client_auth.get("/presupuesto/api/areas/no-existe-xyz/panel/")
        self.assertEqual(r.status_code, 404)

    # ── La razón de existir del panel ──────────────────────────────

    def test_area_sin_eventos_igual_muestra_su_plan(self):
        """Educación tiene 0 eventos. Su panel NO puede salir vacío."""
        p = self._panel(EDUCACION)
        self.assertEqual(p["tiles"]["n_eventos"], 0,
                         "si Educación ya captura eventos, revisa este test")
        # Aun sin un solo evento tiene proyecto, plan y módulos propios.
        self.assertGreater(p["tiles"]["n_proyectos"], 0)
        self.assertGreater(len(p["modulos"]), 0)

    def test_area_sin_actividades_pero_con_contratos_lo_dice(self):
        """Infraestructura: contratos que no cuelgan de ninguna actividad."""
        p = self._panel(INFRAESTRUCTURA)
        if not p["tiles"]["n_contratos"]:
            self.skipTest("Infraestructura ya no tiene contratos en esta BD")
        # El panel no los esconde: los cuenta como sueltos.
        self.assertEqual(
            p["sueltos"]["contratos_sin_actividad"]["n"],
            p["tiles"]["n_contratos"] - p["tiles"]["n_contratos_enganchados"])

    def test_el_ancla_es_el_plan_no_el_evento(self):
        """Deporte tiene muchas más actividades que eventos: deben salir todas."""
        p = self._panel(DEPORTE)
        self.assertGreater(p["tiles"]["n_actividades"], p["tiles"]["n_eventos"],
                           "el escenario que motivó el panel ya no aplica")
        self.assertEqual(len(p["plan"]), p["tiles"]["n_actividades"])

    # ── Coherencia de los sueltos ──────────────────────────────────

    def test_los_sueltos_cuadran_con_los_tiles(self):
        for sid in (CULTURA, DEPORTE, EDUCACION, INFRAESTRUCTURA, SEGURIDAD):
            p = self._panel(sid)
            t, s = p["tiles"], p["sueltos"]
            with self.subTest(subgrupo=sid):
                self.assertEqual(s["actividades_sin_kpi"]["n"],
                                 t["n_actividades"] - t["n_actividades_con_kpi"])
                self.assertEqual(s["eventos_sin_actividad"]["n"],
                                 t["n_eventos"] - t["n_eventos_con_actividad"])
                self.assertEqual(s["contratos_sin_actividad"]["n"],
                                 t["n_contratos"] - t["n_contratos_enganchados"])
                # `de` nunca puede ser menor que `n`: sería un porcentaje > 100.
                for bloque in s.values():
                    self.assertLessEqual(bloque["n"], bloque["de"])

    def test_cada_suelto_explica_que_significa(self):
        """Un número sin explicación no sirve: el área no sabe qué hacer con él."""
        s = self._panel(CULTURA)["sueltos"]
        for clave, bloque in s.items():
            with self.subTest(suelto=clave):
                self.assertTrue(bloque["que_significa"].strip())

    # ── Registro de módulos ────────────────────────────────────────

    def test_educacion_jala_jovenes_y_colegios(self):
        codigos = {m["codigo"] for m in self._panel(EDUCACION)["modulos"]}
        self.assertIn("jovenes_a_la_e", codigos)
        self.assertIn("colegios", codigos)

    def test_cultura_jala_festivales(self):
        codigos = {m["codigo"] for m in self._panel(CULTURA)["modulos"]}
        self.assertIn("festivales", codigos)

    def test_los_transversales_aparecen_donde_hay_datos(self):
        """El Banco no es de Deporte: es de quien tenga una convocatoria.

        Seguridad también tiene un evento BANCO_INICIATIVAS, y por eso le
        aparece la tarjeta. Si esto se rompe, alguien volvió a cablear el
        módulo a un área fija.
        """
        from apps.login.models import Evento

        for sid in (DEPORTE, SEGURIDAD):
            tiene_evento = Evento.objects.filter(
                subgrupo_id=sid, tipo_evento_id="BANCO_INICIATIVAS").exists()
            codigos = {m["codigo"] for m in self._panel(sid)["modulos"]}
            with self.subTest(subgrupo=sid):
                self.assertEqual(tiene_evento, "banco_iniciativas" in codigos)

    def test_los_transversales_cuentan_lo_del_area_no_lo_global(self):
        from apps.login.models import Evento

        p = self._panel(SEGURIDAD)
        cursos = next((m for m in p["modulos"] if m["codigo"] == "cursos"), None)
        if cursos is None:
            self.skipTest("Seguridad ya no tiene cursos en esta BD")
        propios = Evento.objects.filter(
            subgrupo_id=SEGURIDAD,
            tipo_evento_id__in=["CURSO", "CAPACITACION"]).count()
        self.assertEqual(cursos["conteo"], propios)

    def test_area_sin_modulo_propio_no_inventa_tarjetas(self):
        """10 de las 15 áreas no tienen módulo propio. Deben devolver []."""
        from apps.presupuesto.services.modulos_area import modulos_de
        self.assertEqual(modulos_de(10), [])   # Ambiente

    # ── HTTP ───────────────────────────────────────────────────────

    def test_endpoint_exige_sesion(self):
        r = self.client_anon.get(reverse("presupuesto:api_area_panel", args=["cultura"]))
        self.assertIn(r.status_code, (301, 302, 401, 403))

    def test_endpoint_responde_el_panel(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.client_auth.get(reverse("presupuesto:api_area_panel", args=["cultura"]))
        self.assertEqual(r.status_code, 200)
        d = r.json()
        for clave in ("area", "tiles", "plan", "contratos", "sueltos", "modulos"):
            self.assertIn(clave, d)

    def test_no_se_puede_enganchar_a_una_actividad_de_otra_area(self):
        """Si no, un área le cuelga su contrato al plan de otra y la
        trazabilidad queda peor que sin enganchar nada."""
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        ajena = self._panel(SEGURIDAD)["plan"]
        propio = self._panel(CULTURA)["contratos"]
        if not ajena or not propio:
            self.skipTest("Faltan datos para cruzar áreas en esta BD")
        r = self.client_auth.post(
            reverse("presupuesto:api_area_vincular_contrato", args=["cultura"]),
            data={"contrato_id": propio[0]["id"],
                  "actividad_plan_id": ajena[0]["actividad_plan_id"]},
            content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_enganchar_sin_datos_falla_limpio(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.client_auth.post(
            reverse("presupuesto:api_area_vincular_contrato", args=["cultura"]),
            data={}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
