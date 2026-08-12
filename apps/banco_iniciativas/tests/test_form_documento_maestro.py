"""Tests del formulario público reingenierizado — DOCUMENTO MAESTRO 2026-07-29.

READ-ONLY: solo construyen `InscripcionBancoForm` y llaman `is_valid()`. Nunca
`save()`: la BD es la de producción (externa, compartida) y estos tests corren
en cada push.

⚠️ HABEAS DATA: todos los datos son INVENTADOS. innovaK es un repositorio
público — ni un nombre, ni una cédula, ni una dirección real de la BD entra
acá. Los nombres son "Prueba", las cédulas empiezan por 1000000, los correos
son `@example.com` y las direcciones no existen.

Lo que fijan estos tests:
  1. Los 14 campos que el documento RETIRA ya no se capturan (y sus columnas
     siguen en el modelo, porque el piloto tiene dato).
  2. Los campos nuevos de las 9 secciones existen.
  3. Las validaciones que el documento exige: 200 caracteres (§7.1/§7.2), 100
     palabras (§7.10), sede en NULL controlado (§2), tope de enfoques (§5.2),
     nivel de espacio coherente (§4.2/§7.9.1), cédula cruzada (§9), compuerta
     presupuestal (§8.5).
  4. Que el estrato certificado por IDECA (§7.9.2) NO sea un campo del POST.
"""
import json
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile


PDF_MINIMO = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG_MINIMO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
    b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _archivo(nombre, contenido, mime):
    return SimpleUploadedFile(nombre, contenido, content_type=mime)


class FormDocumentoMaestroTests(unittest.TestCase):
    """El formulario de las 9 secciones. Todo el payload es sintético."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.banco_iniciativas.models import Escenario
        from apps.georeferenciacion.models.models_localizacion import Barrio

        cls.barrio = Barrio.objects.order_by("codigo").first()
        cls.esc_practica = list(
            Escenario.objects.filter(activo=True, categoria_pot="otros_practica")
            .order_by("codigo")[:2]
        )
        cls.esc_dotacional = list(
            Escenario.objects.filter(activo=True, categoria_pot="otros_dotacionales")
            .order_by("codigo")[:1]
        )
        if not (cls.barrio and cls.esc_practica and cls.esc_dotacional):
            raise unittest.SkipTest(
                "Catálogos incompletos en esta BD (barrio / escenario por nivel)."
            )

    # ── helpers ─────────────────────────────────────────────────
    def _form(self, **cambios):
        """Payload válido completo; `cambios` sobrescribe o borra (valor None)."""
        from apps.banco_iniciativas.forms.inscripcion import (
            InscripcionBancoForm, MIN_CARACTERES_NARRATIVA,
            MIN_PALABRAS_AMBIENTAL,
        )

        largo = "Descripcion sintetica de la situacion del territorio. " * 8
        assert len(largo) >= MIN_CARACTERES_NARRATIVA
        sustento = " ".join(["mitigacion"] * (MIN_PALABRAS_AMBIENTAL + 5))

        data = {
            # §1
            "nombre_organizacion": "Colectivo Sintetico de Pruebas",
            "tipo_organizacion": 8,
            "numero_soporte_legal": "900000001",
            "rep_nombre1": "Nombre", "rep_apellido1": "Prueba",
            "rep_tipo_doc": 1, "rep_numero_doc": "1000000001",
            # §2
            "telefono": "3000000000", "correo": "prueba@example.com",
            "tiene_sede_fisica": "si",
            "barrio": self.barrio.codigo,
            "direccion": "Calle 100 # 100 - 100",
            "estrato": 2,
            # §3
            "tamano_staff_num": 45,
            "anios_experiencia": 10,
            "composicion_organizacion": "solo_mujeres",
            "rango_poblacion": 8,
            # §4
            "modalidad_actividad": 1,
            "disciplina_actividad_otro": "Disciplina sintetica",
            "arraigo_red": "otros_practica",
            "escenarios_actuales": [e.codigo for e in self.esc_practica],
            "arraigo_espacio_nombre": "Espacio sintetico",
            "arraigo_direccion": "Calle 101 # 101 - 101",
            "arraigo_estrato": 2,
            "arraigo_actividad": "Actividad sintetica los sabados.",
            # §5
            "rango_etarios": [6, 7],
            "enfoques": json.dumps([
                {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1,
                 "opciones": ["c52_mujer_genero__femenino"]},
                {"seccion": "5.2", "familia": "c52_discapacidad", "orden": 2,
                 "opciones": ["c52_discapacidad__fisica"]},
                {"seccion": "7.8", "familia": "p78_mujer", "orden": 1,
                 "opciones": ["p78_mujer__liderazgo"]},
                {"seccion": "7.8", "familia": "p78_discapacidad", "orden": 2,
                 "opciones": []},
            ]),
            # §6
            "participa_espacio": "si", "instancias": [1, 3],
            "beneficio_alk": 7,
            # §7
            "problematica": largo, "justificacion": largo,
            "modalidad_propuesta": 2, "otros_deportes": "Disciplina sintetica",
            "objetivo_general": "Objetivo general sintetico.",
            "objetivos_especificos": json.dumps(["Uno", "Dos", "Tres"]),
            "cobertura_staff": "ge_50", "cobertura_comunidad": "gt_80",
            "cobertura_indirectos": "gt_200",
            "ciclo_vital": [6, 8],
            "diversidad_genero_propuesta": "solo_mujeres",
            "ejecucion_red": "otros_dotacionales",
            "escenarios": [e.codigo for e in self.esc_dotacional],
            "nombre_espacio_ejecucion": "Espacio sintetico de ejecucion",
            "direccion_espacio_ejecucion": "Carrera 102 # 102 - 102",
            "ejecucion_estrato": 3,
            "sostenibilidad_ambiental": "si", "sostenibilidad_sustento": sustento,
            # §8
            "metodologia": "Metodologia sintetica.",
            "actividades": json.dumps([
                {"nombre": "Actividad 1", "descripcion": "Descripcion 1"},
                {"nombre": "Actividad 2", "descripcion": "Descripcion 2"},
            ]),
            "cronograma": json.dumps([
                {"actividad_idx": 0, "mes": 1, "semana": 1},
                {"actividad_idx": 1, "mes": 4, "semana": 4},
            ]),
            "equipo": json.dumps([
                {"nombre": "Integrante Prueba", "nivel_formacion_codigo": 10,
                 "rol": "Coordinacion"},
            ]),
            "presupuesto": json.dumps([
                {"actividad_idx": 0, "descripcion_rubro": "Rubro sintetico",
                 "cantidad": 10, "valor_unitario": 100000},
            ]),
            # §9
            "compromiso_redes": "on", "compromiso_carta_1ano": "on",
            "compromiso_actualizacion": "on", "declaracion_buena_fe": "on",
            "firma_cedula": "1000000001", "firma_fecha": "2026-01-15",
        }
        data.update(cambios)
        for clave in [k for k, v in list(data.items()) if v is None]:
            data.pop(clave)

        files = {
            "soporte_legal": _archivo("soporte.pdf", PDF_MINIMO, "application/pdf"),
            "cedula_representante": _archivo("cedula.pdf", PDF_MINIMO,
                                             "application/pdf"),
            "firma": _archivo("firma.png", PNG_MINIMO, "image/png"),
        }
        # Soportes del Bloque 1 (Documento Guía 2026-08-10): el payload base
        # responde cosas que puntúan, así que sin ellos el formulario ya no es
        # válido — que es exactamente la regla nueva. Se agregan todos para que
        # estos tests sigan probando lo suyo y no la compuerta de soportes,
        # que tiene su propia clase más abajo.
        from apps.banco_iniciativas.services.matriz_oficial import (
            SOPORTES_POR_SUBCRITERIO)
        for clave in set(SOPORTES_POR_SUBCRITERIO.values()):
            files.setdefault(
                clave, _archivo(f"{clave}.pdf", PDF_MINIMO, "application/pdf"))
        return InscripcionBancoForm(data=data, files=files)

    def _errores(self, **cambios):
        form = self._form(**cambios)
        form.is_valid()
        return form.errors

    # ── 1. Lo que se retiró ─────────────────────────────────────
    def test_los_campos_de_url_ya_no_se_capturan(self):
        """§1.4/§9: el documento exige cargue real dentro del aplicativo.

        Pegar un enlace de OneDrive dejaba el soporte fuera de nuestra
        custodia; ahora el archivo entra al aplicativo y se cifra en Mongo.
        """
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        for retirado in ("soporte_legal_url", "propuesta_url", "firma_imagen_url"):
            self.assertNotIn(retirado, campos)
        # …y los reemplazos son campos de archivo obligatorios.
        for anexo in ("soporte_legal", "cedula_representante", "firma"):
            self.assertIn(anexo, campos)
            self.assertTrue(campos[anexo].required)

    def test_las_columnas_de_url_siguen_en_el_modelo(self):
        """Se retira la CAPTURA, no el histórico.

        Las 24 inscripciones del piloto tienen dato en esas columnas y el panel
        del organizador las muestra (`views/organizador.py`, `api/serializers.py`).
        Borrarlas del modelo rompería el detalle de todas ellas.
        """
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        columnas = {f.name for f in InscripcionBancoIniciativa._meta.fields}
        for columna in ("soporte_legal_url", "propuesta_url", "firma_imagen_url",
                        "uso_beneficio", "impacto_politicas", "impacto_justificacion",
                        "requerimiento_detalle", "espacio_participacion"):
            self.assertIn(columna, columnas)

    def test_campos_retirados_del_formulario(self):
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        for retirado in (
            "redes_otra", "impacto_politicas", "impacto_justificacion",
            "uso_beneficio", "implementos", "categorias_material",
            "requerimiento_detalle", "tipos_apoyo", "espacio_participacion",
            "espacio_participacion_otro",
        ):
            self.assertNotIn(retirado, campos, f"{retirado} debió salir del form")

    def test_estrato_sin_opcion_5(self):
        """El documento elimina explícitamente el estrato 5 (y el CHECK es 1-4)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        for campo in ("estrato", "arraigo_estrato", "ejecucion_estrato"):
            valores = [v for v, _ in campos[campo].choices if v != ""]
            self.assertEqual(valores, [1, 2, 3, 4], campo)

    def test_el_estrato_de_ideca_no_es_un_campo_del_post(self):
        """§7.9.2: los 9 puntos de estrato los certifica IDECA, no el proponente.

        Si el campo existiera, cualquiera podría postear `estrato=1` y regalarse
        el máximo. El servidor lo resuelve del punto (ver
        `certificar_estrato_ejecucion`).
        """
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        for prohibido in ("ejecucion_estrato_ideca", "ejecucion_fuera_kennedy",
                          "ejecucion_geo_metodo", "estrato_ideca_org", "radicado_at"):
            self.assertNotIn(prohibido, campos)

    # ── 2. Lo que se agregó ─────────────────────────────────────
    def test_los_campos_nuevos_de_las_9_secciones_existen(self):
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        for nuevo in (
            # §2
            "tiene_sede_fisica", "redes_web",
            # §3
            "tamano_staff_num",
            # §4
            "modalidad_actividad", "disciplina_actividad",
            "disciplina_actividad_otro", "arraigo_red", "arraigo_escenario_otro",
            "arraigo_espacio_nombre", "arraigo_direccion", "arraigo_lon",
            "arraigo_lat", "arraigo_estrato", "arraigo_actividad",
            # §5 y §7.8
            "enfoques",
            # §6
            "instancias", "beneficio_alk",
            # §7
            "problematica", "justificacion", "modalidad_propuesta",
            "objetivo_general", "objetivos_especificos", "cobertura_staff",
            "cobertura_comunidad", "cobertura_indirectos",
            "diversidad_genero_propuesta", "ejecucion_red",
            "ejecucion_escenario_otro", "ejecucion_lon", "ejecucion_lat",
            "ejecucion_estrato", "sostenibilidad_ambiental",
            "sostenibilidad_sustento",
            # §8
            "metodologia", "actividades", "cronograma", "equipo", "presupuesto",
            # §9
            "declaracion_buena_fe",
        ):
            self.assertIn(nuevo, campos, f"falta {nuevo}")

    def test_los_codigos_de_cobertura_son_los_que_acepta_la_bd(self):
        """§7.5: el código es la llave con la que la rúbrica busca el peso.

        Las choices se importan del modelo, que es el espejo del CHECK del
        script 013. Si el form emitiera otro código, Postgres rechazaría la
        radicación completa.
        """
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        campos = InscripcionBancoForm().fields
        esperado = {
            "cobertura_staff": {"ge_50", "11_49", "4_10", "min_3"},
            "cobertura_comunidad": {"gt_80", "51_80", "41_60", "21_40", "min_20"},
            "cobertura_indirectos": {"gt_200", "101_200", "51_100", "hasta_50"},
            "diversidad_genero_propuesta": {
                "solo_mujeres", "mayor_mujeres", "lgtbiq", "mixta_diversidades",
                "mayor_hombres", "solo_hombres"},
        }
        for campo, codigos in esperado.items():
            valores = {v for v, _ in campos[campo].choices if v != ""}
            self.assertEqual(valores, codigos, campo)

    # ── 3. Validaciones del documento ───────────────────────────
    def test_payload_completo_es_valido(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_narrativa_exige_200_caracteres(self):
        errores = self._errores(problematica="Muy corto.", justificacion="Corto.")
        self.assertIn("problematica", errores)
        self.assertIn("justificacion", errores)

    def test_ambiental_si_exige_100_palabras(self):
        errores = self._errores(
            sostenibilidad_sustento=" ".join(["palabra"] * 99))
        self.assertIn("sostenibilidad_sustento", errores)

    def test_ambiental_no_no_exige_sustento(self):
        form = self._form(sostenibilidad_ambiental="no",
                          sostenibilidad_sustento=None)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        # Si respondió NO, el sustento no aplica: no se guarda texto huérfano.
        self.assertEqual(form.cleaned_data["sostenibilidad_sustento"], "")

    def test_sin_sede_fisica_no_reclama_barrio_ni_direccion_ni_estrato(self):
        """§2: 'No' oculta 2.3-2.5 y guarda NULL controlado, sin error."""
        form = self._form(tiene_sede_fisica="no", barrio=None, direccion=None,
                          estrato=None)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        for campo in ("barrio", "direccion", "estrato"):
            self.assertIsNone(form.cleaned_data[campo])

    def test_con_sede_fisica_si_los_reclama(self):
        errores = self._errores(barrio=None, direccion=None, estrato=None)
        for campo in ("barrio", "direccion", "estrato"):
            self.assertIn(campo, errores)

    def test_enfoques_52_tope_de_mujer_mas_3_adicionales(self):
        """§5.2: 'Mujer y Género' + hasta 3 adicionales. La quinta no suma."""
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1},
            {"seccion": "5.2", "familia": "c52_discapacidad", "orden": 2},
            {"seccion": "5.2", "familia": "c52_etnico_narp", "orden": 3},
            {"seccion": "5.2", "familia": "c52_etnico_indigena", "orden": 4},
            {"seccion": "5.2", "familia": "c52_victima", "orden": 5},
        ]))
        self.assertIn("enfoques", errores)

    def test_enfoques_ninguno_es_excluyente(self):
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "5.2", "familia": "c52_ninguno", "orden": 1},
            {"seccion": "5.2", "familia": "c52_discapacidad", "orden": 2},
        ]))
        self.assertIn("enfoques", errores)

    def test_enfoques_no_admite_dos_veces_la_misma_posicion(self):
        """§7.8: el orden reparte 4/3/2/1. Dos en la misma posición no se
        pueden desempatar sin inventar."""
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1},
            {"seccion": "7.8", "familia": "p78_mujer", "orden": 1},
            {"seccion": "7.8", "familia": "p78_genero", "orden": 1},
        ]))
        self.assertIn("enfoques", errores)

    def test_enfoques_opcion_de_otra_familia_falla(self):
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1,
             "opciones": ["c52_discapacidad__fisica"]},
        ]))
        self.assertIn("enfoques", errores)

    def test_enfoques_familia_de_otra_seccion_falla(self):
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "5.2", "familia": "p78_migrante", "orden": 1},
        ]))
        self.assertIn("enfoques", errores)

    def test_enfoques_5_2_es_obligatorio(self):
        errores = self._errores(enfoques=json.dumps([
            {"seccion": "7.8", "familia": "p78_mujer", "orden": 1},
        ]))
        self.assertIn("enfoques", errores)

    def test_el_orden_de_activacion_se_conserva(self):
        """El orden que manda el ciudadano es el que sale de `clean`."""
        form = self._form(enfoques=json.dumps([
            {"seccion": "7.8", "familia": "p78_discapacidad", "orden": 2},
            {"seccion": "7.8", "familia": "p78_mujer", "orden": 1},
            {"seccion": "5.2", "familia": "c52_mujer_genero", "orden": 1},
        ]))
        self.assertTrue(form.is_valid(), form.errors.as_json())
        secuencia = [f["familia"] for f in form.cleaned_data["enfoques"]["7.8"]]
        self.assertEqual(secuencia, ["p78_mujer", "p78_discapacidad"])

    def test_escenario_de_otro_nivel_no_se_acepta(self):
        """§4.2/§7.9.1: el nivel habilita SUS botones. Mezclar niveles deja el
        puntaje indefendible (el nivel vale 4/2/1/0 y 9/6/3/0)."""
        errores = self._errores(
            escenarios_actuales=[e.codigo for e in self.esc_dotacional])
        self.assertIn("escenarios_actuales", errores)

    def test_nivel_sin_botones_ni_otro_falla(self):
        errores = self._errores(escenarios=[], ejecucion_escenario_otro=None)
        self.assertIn("escenarios", errores)

    def test_nivel_con_solo_otro_es_valido(self):
        form = self._form(escenarios=[],
                          ejecucion_escenario_otro="Espacio no listado")
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_instancias_obligatorias_si_declara_participar(self):
        errores = self._errores(instancias=[])
        self.assertIn("instancias", errores)

    def test_sin_participacion_no_reclama_instancias(self):
        form = self._form(participa_espacio="no", instancias=[])
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_objetivos_especificos_son_exactamente_3(self):
        for lista in (["Uno"], ["Uno", "Dos"], ["Uno", "Dos", "Tres", "Cuatro"]):
            with self.subTest(n=len(lista)):
                errores = self._errores(objetivos_especificos=json.dumps(lista))
                self.assertIn("objetivos_especificos", errores)

    def test_cronograma_fuera_de_la_matriz_4x4_falla(self):
        for celda in ({"actividad_idx": 0, "mes": 5, "semana": 1},
                      {"actividad_idx": 0, "mes": 1, "semana": 9}):
            with self.subTest(celda=celda):
                errores = self._errores(cronograma=json.dumps([celda]))
                self.assertIn("cronograma", errores)

    def test_toda_actividad_necesita_cronograma(self):
        errores = self._errores(cronograma=json.dumps(
            [{"actividad_idx": 0, "mes": 1, "semana": 1}]))
        self.assertIn("cronograma", errores)

    def test_cronograma_no_puede_apuntar_a_una_actividad_inexistente(self):
        errores = self._errores(cronograma=json.dumps([
            {"actividad_idx": 0, "mes": 1, "semana": 1},
            {"actividad_idx": 7, "mes": 2, "semana": 2},
        ]))
        self.assertIn("cronograma", errores)

    def test_presupuesto_no_acepta_cantidad_cero(self):
        """CHECK de la BD: `cantidad > 0`. Se ataja en el form para que el
        ciudadano vea el error en su campo y no un 500."""
        errores = self._errores(presupuesto=json.dumps([
            {"actividad_idx": 0, "descripcion_rubro": "Rubro", "cantidad": 0,
             "valor_unitario": 1000},
        ]))
        self.assertIn("presupuesto", errores)

    def test_presupuesto_bloquea_el_tope_maximo(self):
        """§8.5: «Ajuste de presupuesto requerido»."""
        from apps.banco_iniciativas.forms.inscripcion import (
            MENSAJE_TOPE_PRESUPUESTAL, TOPE_PRESUPUESTAL_MAXIMO,
        )
        errores = self._errores(presupuesto=json.dumps([
            {"actividad_idx": 0, "descripcion_rubro": "Rubro",
             "cantidad": 1, "valor_unitario": TOPE_PRESUPUESTAL_MAXIMO + 1},
        ]))
        self.assertIn("presupuesto", errores)
        self.assertIn(MENSAJE_TOPE_PRESUPUESTAL, str(errores["presupuesto"]))

    def test_presupuesto_no_acepta_valor_total_del_navegador(self):
        """`valor_total` es GENERATED ALWAYS en la BD: si el navegador lo
        mandara, un POST directo podría radicar un total que no corresponde a
        cantidad × unitario y saltarse el tope. Se ignora."""
        form = self._form(presupuesto=json.dumps([
            {"actividad_idx": 0, "descripcion_rubro": "Rubro", "cantidad": 2,
             "valor_unitario": 1000, "valor_total": 999999999},
        ]))
        self.assertTrue(form.is_valid(), form.errors.as_json())
        fila = form.cleaned_data["presupuesto"][0]
        self.assertNotIn("valor_total", fila)

    def test_equipo_exige_nombre_rol_y_formacion(self):
        errores = self._errores(equipo=json.dumps([{"nombre": "Integrante"}]))
        self.assertIn("equipo", errores)

    def test_equipo_rechaza_nivel_de_formacion_inexistente(self):
        errores = self._errores(equipo=json.dumps([
            {"nombre": "Integrante", "rol": "Rol", "nivel_formacion_codigo": 9999},
        ]))
        self.assertIn("equipo", errores)

    def test_colecciones_con_json_invalido_fallan_con_mensaje_del_campo(self):
        for campo in ("enfoques", "actividades", "cronograma", "equipo",
                      "presupuesto", "objetivos_especificos"):
            with self.subTest(campo=campo):
                errores = self._errores(**{campo: "no-es-json"})
                self.assertIn(campo, errores)

    def test_declaracion_de_buena_fe_es_obligatoria(self):
        """§9: es un checkbox jurídicamente separado de los 3 compromisos."""
        errores = self._errores(declaracion_buena_fe=None)
        self.assertIn("declaracion_buena_fe", errores)

    def test_cedula_de_firma_cruzada_con_el_representante(self):
        errores = self._errores(firma_cedula="1000000009")
        self.assertIn("firma_cedula", errores)

    def test_firma_en_pdf_tambien_vale(self):
        """§9 admite lienzo Canvas (PNG/JPG) o PDF firmado."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        form = self._form()
        datos = dict(form.data)
        archivos = {
            "soporte_legal": _archivo("s.pdf", PDF_MINIMO, "application/pdf"),
            "cedula_representante": _archivo("c.pdf", PDF_MINIMO, "application/pdf"),
            "firma": _archivo("firma.pdf", PDF_MINIMO, "application/pdf"),
        }
        # Igual que en `_form`: los soportes del Bloque 1 hacen falta para que
        # el formulario valide; acá lo que se prueba es la firma en PDF.
        from apps.banco_iniciativas.services.matriz_oficial import (
            SOPORTES_POR_SUBCRITERIO)
        for clave in set(SOPORTES_POR_SUBCRITERIO.values()):
            archivos.setdefault(
                clave, _archivo(f"{clave}.pdf", PDF_MINIMO, "application/pdf"))
        otro = InscripcionBancoForm(data=datos, files=archivos)
        self.assertTrue(otro.is_valid(), otro.errors.as_json())

    def test_soporte_legal_solo_acepta_pdf(self):
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        form = self._form()
        archivos = {
            "soporte_legal": _archivo("s.png", PNG_MINIMO, "image/png"),
            "cedula_representante": _archivo("c.pdf", PDF_MINIMO, "application/pdf"),
            "firma": _archivo("f.png", PNG_MINIMO, "image/png"),
        }
        otro = InscripcionBancoForm(data=dict(form.data), files=archivos)
        otro.is_valid()
        self.assertIn("soporte_legal", otro.errors)

    def test_firma_sin_archivo_falla(self):
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        form = self._form()
        otro = InscripcionBancoForm(data=dict(form.data), files={
            "soporte_legal": _archivo("s.pdf", PDF_MINIMO, "application/pdf"),
            "cedula_representante": _archivo("c.pdf", PDF_MINIMO, "application/pdf"),
        })
        otro.is_valid()
        self.assertIn("firma", otro.errors)

    def test_firma_no_puede_ser_futura(self):
        from django.utils import timezone
        futuro = timezone.localdate().replace(year=timezone.localdate().year + 1)
        errores = self._errores(firma_fecha=futuro.isoformat())
        self.assertIn("firma_fecha", errores)

    def test_media_coordenada_se_descarta_entera(self):
        """Un punto a medias pasaría el CHECK de la BD y no ubica nada."""
        form = self._form(arraigo_lon=-74.15, arraigo_lat=None,
                          ejecucion_lat=4.62, ejecucion_lon=None)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        for campo in ("arraigo_lon", "arraigo_lat", "ejecucion_lon",
                      "ejecucion_lat"):
            self.assertIsNone(form.cleaned_data[campo])

    def test_coordenada_completa_sobrevive(self):
        form = self._form(ejecucion_lon=-74.15, ejecucion_lat=4.62)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data["ejecucion_lon"], -74.15)
        self.assertEqual(form.cleaned_data["ejecucion_lat"], 4.62)


class CertificacionIdecaTests(unittest.TestCase):
    """§7.9.2 — la certificación de estrato es del servidor y es auditable."""

    def test_sin_punto_no_hay_certificacion(self):
        from apps.banco_iniciativas.forms.inscripcion import (
            certificar_estrato_ejecucion,
        )
        for lon, lat in ((None, None), (-74.15, None), (None, 4.62)):
            with self.subTest(lon=lon, lat=lat):
                r = certificar_estrato_ejecucion(lon, lat)
                self.assertIsNone(r["estrato"])
                self.assertIsNone(r["metodo"])

    def test_punto_fuera_de_kennedy_no_puntua(self):
        """La focalización premia operar EN la localidad. Bogotá centro
        (Plaza de Bolívar, ~-74.076 / 4.598) está fuera de Kennedy."""
        from apps.banco_iniciativas.forms.inscripcion import (
            certificar_estrato_ejecucion,
        )
        r = certificar_estrato_ejecucion(-74.0760, 4.5981)
        if r["fuera_kennedy"] is None:
            self.skipTest("Contorno de Kennedy no disponible en esta BD.")
        self.assertTrue(r["fuera_kennedy"])
        self.assertIsNone(r["estrato"])

    def test_el_estrato_certificado_nunca_sale_del_dominio_1_a_4(self):
        """Catastro devuelve 5 y 6; el CHECK de la BD es 1-4. Un 5 sin recortar
        tumbaría la radicación completa."""
        from apps.banco_iniciativas.forms.inscripcion import (
            ESTRATOS_VALIDOS, certificar_estrato_ejecucion,
        )
        # Puntos sintéticos dentro del polígono de Kennedy.
        for lon, lat in ((-74.1600, 4.6300), (-74.1470, 4.6180)):
            with self.subTest(lon=lon, lat=lat):
                r = certificar_estrato_ejecucion(lon, lat)
                self.assertIn(r["estrato"], (None, *ESTRATOS_VALIDOS))

    def test_punto_en_kennedy_se_certifica_con_metodo_auditable(self):
        """El método viaja junto al estrato: alimenta un puntaje, así que hay
        que poder decir CÓMO se determinó ('contenido', 'cercano', 'entorno')."""
        from apps.banco_iniciativas.forms.inscripcion import (
            ESTRATOS_VALIDOS, certificar_estrato_ejecucion,
        )
        r = certificar_estrato_ejecucion(-74.1470, 4.6180)
        if r["estrato"] is None:
            self.skipTest("La capa `manzana_estrato` no resuelve este punto.")
        self.assertIn(r["estrato"], ESTRATOS_VALIDOS)
        self.assertTrue(r["metodo"])
        self.assertFalse(r["fuera_kennedy"])


# ── Soportes obligatorios del Bloque 1 (Documento Guía 2026-08-10) ──────────

class _Cod:
    """Objeto de catálogo mínimo: al motor solo le importa el `codigo`."""

    def __init__(self, codigo):
        self.codigo = codigo


class SoportesCondicionalesTests(unittest.TestCase):
    """El soporte se exige donde HAY puntaje que respaldar, no siempre.

    La obligatoriedad se deriva del motor (`_exigir_soportes_del_bloque_1`) y
    no de reglas copiadas en el formulario: si se duplicaran los brackets, un
    día se desincronizarían y el sistema exigiría —o perdonaría— un soporte
    que no corresponde.
    """

    #: Respuestas que puntúan en los 8 subcriterios con soporte.
    RESPUESTAS_QUE_PUNTUAN = {
        "tamano_staff_num": 45,
        "anios_experiencia": _Cod(10),
        "composicion_organizacion": "solo_mujeres",
        "rango_poblacion": _Cod(8),
        "arraigo_estrato": 1,
        "rango_etarios": [_Cod(6)],
        "instancias": [_Cod(1)],
        "beneficio_alk": _Cod(7),
    }

    def _exigidos(self, cleaned):
        from apps.banco_iniciativas.forms import InscripcionBancoForm
        f = InscripcionBancoForm()
        f.cleaned_data = dict(cleaned)
        f._errors = {}
        f._exigir_soportes_del_bloque_1(f.cleaned_data)
        return set(f._errors)

    def test_puntuar_sin_soportes_los_exige_todos(self):
        from apps.banco_iniciativas.services.matriz_oficial import (
            SOPORTES_POR_SUBCRITERIO)
        self.assertEqual(self._exigidos(self.RESPUESTAS_QUE_PUNTUAN),
                         set(SOPORTES_POR_SUBCRITERIO.values()))

    def test_con_los_soportes_cargados_no_hay_error(self):
        faltantes = self._exigidos(self.RESPUESTAS_QUE_PUNTUAN)
        completo = dict(self.RESPUESTAS_QUE_PUNTUAN,
                        **{k: "archivo.pdf" for k in faltantes})
        self.assertEqual(self._exigidos(completo), set())

    def test_lo_que_no_puntua_no_pide_soporte(self):
        """Un colectivo sin instancias no tiene por qué subir actas: pedirle un
        papel que no existe sería una barrera inventada."""
        self.assertEqual(
            self._exigidos({"tamano_staff_num": 0, "arraigo_estrato": 4}), set())

    def test_solo_pide_el_soporte_de_lo_que_si_respondio(self):
        solo_staff = {"tamano_staff_num": 45}
        self.assertEqual(self._exigidos(solo_staff), {"staff_listado"})

    def test_el_estrato_4_no_puntua_y_no_pide_su_soporte(self):
        """§4.2 da 0.0 en estrato 4: no hay puntaje que respaldar."""
        self.assertNotIn("arraigo_uso_espacio",
                         self._exigidos({"arraigo_estrato": 4}))
        self.assertIn("arraigo_uso_espacio",
                      self._exigidos({"arraigo_estrato": 1}))

    def test_el_mensaje_dice_cuanto_se_pierde(self):
        """Un «campo obligatorio» seco no le explica al ciudadano el costo."""
        from apps.banco_iniciativas.forms import InscripcionBancoForm
        f = InscripcionBancoForm()
        f.cleaned_data = {"tamano_staff_num": 45}
        f._errors = {}
        f._exigir_soportes_del_bloque_1(f.cleaned_data)
        mensaje = str(f._errors["staff_listado"][0])
        self.assertIn("§3.1", mensaje)
        self.assertIn("3.0", mensaje)


class CatalogosDeAnexosAlineadosTests(unittest.TestCase):
    """Los tres catálogos de anexos tienen que decir lo mismo.

    El tipo viaja por tres sitios —el CHECK de la BD, el formulario y el
    nombre del archivo en OneDrive— y un desalineado se manifiesta tarde: al
    radicar, con el ciudadano al otro lado.
    """

    def test_todo_soporte_del_motor_tiene_campo_en_el_formulario(self):
        from apps.banco_iniciativas.forms.inscripcion import ANEXOS
        from apps.banco_iniciativas.services.matriz_oficial import (
            SOPORTES_POR_SUBCRITERIO)
        claves = {c for c, _, _, _ in ANEXOS}
        self.assertEqual(set(SOPORTES_POR_SUBCRITERIO.values()) - claves, set())

    def test_todo_anexo_del_formulario_tiene_nombre_en_onedrive(self):
        from apps.banco_iniciativas.forms.inscripcion import ANEXOS
        from apps.documentos.services.onedrive_storage import NOMBRES_ANEXOS
        claves = {c for c, _, _, _ in ANEXOS}
        self.assertEqual(claves - set(NOMBRES_ANEXOS), set())

    def test_los_tipos_caben_en_la_columna_de_la_base(self):
        """`inscripcion_banco_anexo.tipo` es varchar(40)."""
        from apps.banco_iniciativas.forms.inscripcion import ANEXOS
        for clave, _, _, _ in ANEXOS:
            with self.subTest(anexo=clave):
                self.assertLessEqual(len(clave), 40)
