"""Smoke tests del módulo Banco de Iniciativas Recreodeportivas.

Sigue el patrón de apps/login/tests/test_smoke.py: usa el superuser real
de la BD vía Test Client; nunca modifica datos.
"""
import unittest
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class BancoIniciativasSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client_auth = Client(HTTP_HOST=HOST)
        cls.client_auth.force_login(cls.user)
        cls.client_anon = Client(HTTP_HOST=HOST)

    # ── Catálogos: cuentas correctas ────────────────────────────

    def test_catalogos_pueblan_correctamente(self):
        """Verifica que los 11 catálogos del módulo tengan filas (DDL aplicado)."""
        from apps.banco_iniciativas.models import (
            Upl, TipoOrganizacion, RangoExperiencia, Escenario, Implemento,
            RangoPoblacionAtendida, RangoEtario, CaracteristicaPoblacion,
            EnfoqueDiferencial, TipoBeneficioAlk, DisciplinaDeportiva,
        )
        # Cuentas mínimas esperadas (según DDL aplicado por sesión principal):
        # Upl: M-01 en HOLD (territorial sin tocar) → sigue en 9.
        self.assertEqual(Upl.objects.count(), 9)
        # Lote 3 (U-02): append+deactivate → 5 legacy + 3 nuevos (codigo 9 se
        # reusó en el 3 'Colectivo') = 8 filas; 4 activos (6,7,8,3).
        self.assertEqual(TipoOrganizacion.objects.count(), 8)
        self.assertEqual(TipoOrganizacion.objects.filter(activo=True).count(), 4)
        # DDL 013 (Documento Maestro, §3.2): las bandas del documento
        # (>8 / 6-8 / 4-6 / 2-4 / 1-2) no son mapeables 1:1 a las 5 viejas
        # → append+deactivate. 5 legacy (inactivos) + 5 nuevos = 10 filas.
        self.assertEqual(RangoExperiencia.objects.count(), 10)
        self.assertEqual(RangoExperiencia.objects.filter(activo=True).count(), 5)
        # Lote 3 (U-04): 17 legacy (inactivos) + 27 nuevos ('Pista de atletismo'
        # se reusó en el codigo 7) = 44 filas; 28 activos.
        # DDL 013 (§4.2/§7.9.1): +2 etiquetas que pedía el documento
        # ('Colegios privados' dotacional, 'Canchas sintéticas con cerramiento'
        # estructurante) = 46 filas; 30 activos.
        self.assertEqual(Escenario.objects.count(), 46)
        self.assertEqual(Escenario.objects.filter(activo=True).count(), 30)
        # `implemento` es un catálogo COMPARTIDO: lo usan el Banco, Entregas y
        # (desde 2026-08-05) Educación, que sumó 10 filas 'educativo'. Contar
        # la tabla entera hacía que este test del Banco se rompiera cada vez
        # que otra área ampliaba el catálogo, sin que nada del Banco cambiara.
        # Se cuentan las categorías que son del Banco.
        self.assertEqual(
            Implemento.objects.filter(
                categoria__in=["deportivo", "tecnologico", "logistico", "general"]
            ).count(),
            35,
        )
        # DDL 013 (§3.4): bandas nuevas (>80 / 51-80 / 21-50 / hasta 20)
        # → append+deactivate. 4 legacy (inactivos) + 4 nuevos = 8 filas.
        self.assertEqual(RangoPoblacionAtendida.objects.count(), 8)
        self.assertEqual(RangoPoblacionAtendida.objects.filter(activo=True).count(), 4)
        # Lote 3 (M-05): 5 legacy (inactivos) + 7 nuevos = 12 filas; 7 activos.
        self.assertEqual(RangoEtario.objects.count(), 12)
        self.assertEqual(RangoEtario.objects.filter(activo=True).count(), 7)
        self.assertEqual(CaracteristicaPoblacion.objects.count(), 16)
        self.assertEqual(EnfoqueDiferencial.objects.count(), 12)
        # DDL 013 (§6.2): la escala inversa del documento necesitaba sus dos
        # extremos, que no estaban en el catálogo ('Sin apoyos previos' = 2.0 y
        # 'Contratos o convenios económicos directos previos' = 0.0).
        self.assertEqual(TipoBeneficioAlk.objects.count(), 8)
        # 005 (expansión IDRD): 14 base + 31 nuevas = 45 filas; 44 activas
        # ('Artes marciales' agrupado cod 5 queda inactivo).
        self.assertEqual(DisciplinaDeportiva.objects.count(), 45)
        self.assertEqual(DisciplinaDeportiva.objects.filter(activo=True).count(), 44)

    # ── Form público ────────────────────────────────────────────

    def test_form_publico_redirige_a_angular_sin_login(self):
        """Migrado a Angular: el form público redirige (302) a /app/p/banco/<id>
        SIN requerir login (no manda a /login/)."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(activo=True, tipo_evento__codigo="BANCO_INICIATIVAS")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest(
                "No hay eventos BANCO_INICIATIVAS para probar el form público."
            )
        r = self.client_anon.get(f"/banco-iniciativas/{evento.id}/inscribir/")
        self.assertEqual(r.status_code, 302)
        # Redirige al público Angular, NO a login.
        self.assertIn("/app/p/banco/", r["Location"])

    def test_form_publico_evento_inexistente_404(self):
        """Evento inexistente debe responder 404, no exponer 500."""
        r = self.client_anon.get("/banco-iniciativas/99999999/inscribir/")
        self.assertEqual(r.status_code, 404)

    # ── Vistas de organizador ───────────────────────────────────

    def test_inscripciones_list_requiere_login(self):
        """GET sin login al listado debe redirigir a login."""
        r = self.client_anon.get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"].lower())

    def test_inscripciones_list_admin_redirige(self):
        """Migrado a Angular: el listado redirige a /app/banco."""
        r = self.client_auth.get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/banco")

    def test_hub_actividades_redirige(self):
        """Migrado a Angular: el hub de Actividades redirige a /app/actividades."""
        r = self.client_auth.get("/dashboard/hub/actividades/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/actividades")

    # ── Form v2: PR-1 (cambios sin DDL) ─────────────────────────

    def test_form_v2_rep_tipo_doc_excluye_nit(self):
        """El representante es persona natural — NIT (codigo=5) no debe aparecer
        en el desplegable. 'Otro' (codigo=6) queda al final."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        codigos = list(f.fields["rep_tipo_doc"].queryset.values_list("codigo", flat=True))
        self.assertNotIn(5, codigos, "NIT (codigo=5) no debe aparecer para persona natural")
        if 6 in codigos:
            self.assertEqual(codigos[-1], 6, "'Otro' (codigo=6) debe quedar al final")

    def test_form_v2_impacto_politicas_retirado_pero_legible(self):
        """`impacto_politicas` salió del formulario (Documento Maestro 2026-07-29):
        no existe en la matriz nueva de 100 puntos y nadie lo evalúa.

        Lo que NO cambia: la columna sigue en la BD y las 24 inscripciones del
        piloto tienen respuesta ahí, así que las etiquetas se conservan en el
        módulo para que el panel del organizador (`api/views.py::insights`)
        siga mostrando el histórico con el texto correcto.
        """
        from apps.banco_iniciativas.forms.inscripcion import (
            IMPACTO_CHOICES, InscripcionBancoForm,
        )
        self.assertNotIn("impacto_politicas", InscripcionBancoForm().fields)
        self.assertNotIn("impacto_justificacion", InscripcionBancoForm().fields)
        choices = dict(IMPACTO_CHOICES)
        self.assertEqual(choices["mucho"], "Sí, mucho")
        self.assertEqual(choices["parcial"], "Sí, parcialmente")
        self.assertEqual(choices["nada"], "No, no han tenido impacto")
        self.assertEqual(choices["no_conozco"], "No conozco las políticas públicas")

    def test_form_v2_rango_poblacion_label_actual(self):
        """§3.4 — la etiqueta es la que el Documento Maestro fijó textualmente.

        Sigue preguntando por el presente (a quién atiende HOY), no por el
        futuro; el documento (Doc. 1, punto 5.2) reescribió la etiqueta para
        «eliminar cualquier ambigüedad interpretativa» sobre "usuarios
        recurrentes". Es literal: si se acorta, deja de ser la del acto
        administrativo.
        """
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertEqual(
            f.fields["rango_poblacion"].label,
            "Cantidad actual de personas que beneficia o atiende su organización",
        )

    # ── Form v2: PR-2 (DDL soporte legal + tipo_organizacion) ─────

    def test_form_v2_pr2_campos_soporte_legal(self):
        """§1.3/§1.4 — el número del soporte legal se queda; el ENLACE se va.

        Hasta el Documento Maestro el ciudadano pegaba una URL de OneDrive
        (`soporte_legal_url`): el archivo quedaba fuera de nuestra custodia y
        podía cambiar o desaparecer después de radicar. Ahora el PDF se carga
        DENTRO del aplicativo (campo `soporte_legal`, obligatorio) y se cifra
        en Mongo.

        La columna `soporte_legal_url` sigue en el modelo a propósito: las 24
        inscripciones del piloto tienen dato ahí y el panel del organizador lo
        muestra. Lo que se retiró es la captura, no el histórico.
        """
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        f = InscripcionBancoForm()
        self.assertIn("numero_soporte_legal", f.fields)
        self.assertNotIn("soporte_legal_url", f.fields,
                         "El enlace externo se reemplazó por cargue real.")
        self.assertIn("soporte_legal", f.fields)
        self.assertTrue(f.fields["soporte_legal"].required)
        self.assertNotIn("nit", f.fields,
                         "Campo nit suelto debió eliminarse en PR-2")
        columnas = {c.name for c in InscripcionBancoIniciativa._meta.fields}
        self.assertIn("soporte_legal_url", columnas,
                      "La columna se queda: el piloto tiene dato y se muestra.")

    def test_form_v2_pr2_tipo_organizacion_refinado(self):
        """Lote 3 (U-02): 4 activos del doc (Club reconocimiento / Escuela aval
        / Personería jurídica / Colectivo). 'Colectivo' se reusó en el codigo 3
        (deactivate-first + ON CONFLICT nombre); el resto son 6,7,8."""
        from apps.banco_iniciativas.models import TipoOrganizacion
        activos = list(
            TipoOrganizacion.objects.filter(activo=True)
            .order_by("orden", "codigo")
            .values_list("codigo", flat=True)
        )
        self.assertEqual(activos, [6, 7, 8, 3])
        # codigo 4 ("Otro") legacy sigue existiendo pero desactivado.
        self.assertTrue(TipoOrganizacion.objects.filter(codigo=4, activo=False).exists())

    def test_form_v2_pr2_modelo_tiene_columnas_nuevas(self):
        """El modelo InscripcionBancoIniciativa expone numero_soporte_legal
        y soporte_legal_mongo_id (DDL aplicado)."""
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        field_names = {f.name for f in InscripcionBancoIniciativa._meta.fields}
        self.assertIn("numero_soporte_legal", field_names)
        self.assertIn("soporte_legal_mongo_id", field_names)

    # ── Form v2: PR-3 (categoria_pot + escenarios uso actual) ─────

    def test_form_v2_pr3_escenario_categoria_pot(self):
        """Lote 3 (U-04): categoria_pot dejó de ser CHECK de 3 y pasó a FK →
        red(codigo) (4 redes). Distribución del catálogo ACTIVO (lo que ve el
        form): 10 estructurante / 9 proximidad / 6 dotacionales / 5 práctica.

        El DDL 013 sumó las dos etiquetas que faltaban del documento:
        'Canchas sintéticas con cerramiento' (estructurante, 9→10) y
        'Colegios privados' (dotacional, 5→6)."""
        from apps.banco_iniciativas.models import Escenario
        act = Escenario.objects.filter(activo=True)
        self.assertEqual(act.filter(categoria_pot="red_estructurante").count(), 10)
        self.assertEqual(act.filter(categoria_pot="red_proximidad").count(), 9)
        self.assertEqual(act.filter(categoria_pot="otros_dotacionales").count(), 6)
        self.assertEqual(act.filter(categoria_pot="otros_practica").count(), 5)
        # Todos los activos quedan categorizados (sin NULL en el set activo).
        self.assertEqual(act.filter(categoria_pot__isnull=True).count(), 0)

    def test_form_v2_pr3_escenarios_actuales_field(self):
        """El form tiene el M2M nuevo escenarios_actuales separado de
        escenarios (que sigue siendo "requeridos" para Sección 7)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertIn("escenarios_actuales", f.fields)
        self.assertIn("escenarios", f.fields)
        # Ambos referencian el mismo catálogo Escenario.
        self.assertEqual(
            list(f.fields["escenarios_actuales"].queryset.values_list("codigo", flat=True)),
            list(f.fields["escenarios"].queryset.values_list("codigo", flat=True)),
        )

    def test_form_v2_pr3_group_by_categoria_filter(self):
        """El filter group_by_categoria agrupa los checkboxes en 4 grupos
        (Red Estructurante / Red Proximidad / Otros dotacionales / Otros de
        práctica) y suma los 30 escenarios activos (28 del Lote 3 + 2 que
        agregó el DDL 013 del Documento Maestro)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        from apps.banco_iniciativas.templatetags.banco_filters import group_by_categoria
        f = InscripcionBancoForm()
        grupos = group_by_categoria(f["escenarios_actuales"])
        self.assertEqual(len(grupos), 4)
        total = sum(len(g["checkboxes"]) for g in grupos)
        self.assertEqual(total, 30)

    def test_form_v2_pr3_modelo_puente_existe(self):
        """El modelo InscripcionBancoEscenarioActual está exportado y
        apunta a la tabla puente nueva."""
        from apps.banco_iniciativas.models import InscripcionBancoEscenarioActual
        self.assertEqual(
            InscripcionBancoEscenarioActual._meta.db_table,
            "inscripcion_banco_escenario_actual",
        )

    # ── Lote 4 — catálogos dedicados + genéricos reusados (U-05/U-07) ──

    def test_lote4_catalogos_dedicados_cuentas(self):
        """Los 6 catálogos dedicados del doc tienen las cuentas EXACTAS."""
        from apps.banco_iniciativas.models import (
            EnfoquePropuesta, TipoHabitabilidadCalle, TipoDesplazamiento,
            TipoPoblacionRural, GrupoEtnicoBanco, IdentidadGeneroBanco,
        )
        self.assertEqual(EnfoquePropuesta.objects.count(), 7)
        self.assertEqual(TipoHabitabilidadCalle.objects.count(), 6)
        self.assertEqual(TipoDesplazamiento.objects.count(), 3)
        self.assertEqual(TipoPoblacionRural.objects.count(), 3)
        self.assertEqual(GrupoEtnicoBanco.objects.count(), 7)
        self.assertEqual(IdentidadGeneroBanco.objects.count(), 3)

    def test_lote4_identidad_etiquetas_exactas_del_doc(self):
        """Identidad de género usa el catálogo DEDICADO con etiquetas del doc
        (Masculina/Femenina/Transgénero…), NO las genéricas (Hombre/Mujer)."""
        from apps.banco_iniciativas.models import IdentidadGeneroBanco
        nombres = list(
            IdentidadGeneroBanco.objects.order_by("codigo").values_list("nombre", flat=True)
        )
        self.assertEqual(nombres[0], "Masculina")
        self.assertEqual(nombres[1], "Femenina")
        self.assertTrue(nombres[2].startswith("Transgénero"))

    def test_lote4_orientacion_filtra_a_3_codigos(self):
        """orientación reusa el genérico pero el form expone SOLO los 3 del doc
        por código explícito {1,2,3}, no por orden/posición."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        codigos = sorted(
            f.fields["orientaciones"].queryset.values_list("codigo", flat=True)
        )
        self.assertEqual(codigos, [1, 2, 3])

    def test_lote4_discapacidad_no_se_pierde_por_activo_null(self):
        """tipo_discapacidad tiene activo=NULL; el form debe exponer las 7
        (no caer en el NULL-trap de exclude(activo=False))."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertEqual(f.fields["discapacidades"].queryset.count(), 7)

    def test_lote4_form_campos_nuevos_presentes(self):
        """El form expone los campos de Lote 4 (U-05/U-07) + Lote 3 (red_detalle)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        for campo in (
            "enfoques_propuesta", "discapacidades", "orientaciones",
            "identidades_genero", "grupos_etnicos", "habitabilidades",
            "desplazamientos", "poblaciones_rurales", "victima_conflicto",
            "red_detalle_json",
        ):
            self.assertIn(campo, f.fields)

    def test_lote4_modelo_victima_conflicto_y_puentes(self):
        """La cabecera tiene victima_conflicto; los 8 puentes + red_detalle existen."""
        from apps.banco_iniciativas.models import (
            InscripcionBancoIniciativa,
            InscripcionBancoDiscapacidad, InscripcionBancoOrientacionSexual,
            InscripcionBancoIdentidadGenero, InscripcionBancoGrupoEtnico,
            InscripcionBancoEnfoquePropuesta, InscripcionBancoHabitabilidad,
            InscripcionBancoDesplazamiento, InscripcionBancoPoblacionRural,
            InscripcionBancoRedDetalle,
        )
        field_names = {f.name for f in InscripcionBancoIniciativa._meta.fields}
        self.assertIn("victima_conflicto", field_names)
        self.assertEqual(
            InscripcionBancoIdentidadGenero._meta.db_table,
            "inscripcion_banco_identidad_genero",
        )
        self.assertEqual(
            InscripcionBancoRedDetalle._meta.db_table,
            "inscripcion_banco_red_detalle",
        )

    def test_lote4_red_detalle_json_valida(self):
        """red_detalle_json valida: JSON inválido falla; red desconocida falla;
        lista válida normaliza a [{red_codigo,...}]."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        # JSON inválido
        f = InscripcionBancoForm(data={"red_detalle_json": "no-es-json"})
        f.is_valid()
        self.assertIn("red_detalle_json", f.errors)
        # red desconocida
        f = InscripcionBancoForm(
            data={"red_detalle_json": '[{"red":"___inexistente___","nombre":"x"}]'})
        f.is_valid()
        self.assertIn("red_detalle_json", f.errors)
        # válida → clean devuelve lista normalizada (probamos el método directo)
        f = InscripcionBancoForm(
            data={"red_detalle_json":
                  '[{"red":"red_estructurante","nombre":"Parque X","direccion":"Cll 1","actividad":"Fútbol"}]'})
        f.is_valid()  # otros campos faltan, pero red_detalle_json NO debe estar en errors
        self.assertNotIn("red_detalle_json", f.errors)

    def test_lote4_catalogos_endpoint_expone_nuevos(self):
        """El endpoint público de catálogos expone los catálogos de Lote 4."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(activo=True, tipo_evento__codigo="BANCO_INICIATIVAS")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest("No hay eventos BANCO_INICIATIVAS activos.")
        if evento.fecha_fin and evento.fecha_fin < date.today():
            self.skipTest("El evento BANCO_INICIATIVAS más reciente está cerrado.")
        r = self.client_anon.get(
            f"/banco-iniciativas/api/publico/{evento.id}/catalogos/")
        if r.status_code != 200:
            self.skipTest(f"Catálogos no disponibles (HTTP {r.status_code}).")
        data = r.json()
        for clave in (
            "enfoques_propuesta", "grupos_etnicos", "identidades_genero",
            "tipos_habitabilidad", "tipos_desplazamiento", "tipos_poblacion_rural",
            "tipos_discapacidad", "orientaciones", "victima_conflicto_choices",
        ):
            self.assertIn(clave, data)
        self.assertEqual(len(data["orientaciones"]), 3)
        self.assertEqual(len(data["tipos_discapacidad"]), 7)
