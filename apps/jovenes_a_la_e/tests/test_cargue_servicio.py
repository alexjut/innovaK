# -*- coding: utf-8 -*-
"""Reglas del cargue masivo que NO tocan la base (2026-08-12).

Lo que se prueba acá es la decisión de Alex del 2026-08-12: cuando una persona
aparece con dos matrículas en el mismo archivo, **se carga UNA sola y cuál lo
elige quien carga**. El sistema no elige por él, y por eso el servicio se niega
a procesar mientras falte una elección — elegir «la primera» por omisión sería
decidir justo donde se dijo que no.

El caso real que la motivó: el documento 1000494673 aparece en el archivo de
2025 con Técnico Laboral Contable en una institución y Administración de
Empresas en otra.

Estas funciones son puras (listas de dicts entrando y saliendo), así que no
hace falta base ni mocks: el runner del proyecto es de solo lectura contra la
BD compartida y `crear_lote`/`procesar` sí escriben, así que quedan fuera y se
prueban en el smoke E2E manual.
"""
import unittest

from apps.jovenes_a_la_e.services import cargue_beneficiarios as mod


def fila(n, doc, programa="5380", ies="4894", estado="ok"):
    return {
        "fila": n, "estado": estado, "errores": [], "avisos": [],
        "datos": {"documento": doc, "snies_programa": programa, "snies_ies": ies,
                  "nombre1": "MARIA", "apellido1": "PEREZ",
                  "programa": f"PROGRAMA {programa}", "ies_nombre": f"IES {ies}"},
    }


class DocumentosRepetidosTests(unittest.TestCase):

    def test_detecta_la_persona_con_dos_matriculas(self):
        filas = [fila(3, "1"), fila(4, "2"), fila(5, "1", programa="9999", ies="1111")]
        rep = mod.documentos_repetidos(filas)
        self.assertEqual(list(rep), ["1"])
        self.assertEqual([f["fila"] for f in rep["1"]], [3, 5])

    def test_no_cuenta_las_filas_con_error(self):
        # Dos filas rotas del mismo documento no son un caso de elección: son
        # dos filas que hay que corregir en el archivo.
        filas = [fila(3, "1"), fila(4, "1", estado="error")]
        self.assertEqual(mod.documentos_repetidos(filas), {})

    def test_una_sola_matricula_no_es_repetido(self):
        self.assertEqual(mod.documentos_repetidos([fila(3, "1"), fila(4, "2")]), {})


class EleccionesTests(unittest.TestCase):

    def setUp(self):
        self.filas = [fila(3, "1"), fila(4, "2"),
                      fila(5, "1", programa="9999", ies="1111")]

    def test_marca_descartada_la_que_no_se_eligio(self):
        mod.aplicar_elecciones(self.filas, {"1": 3})
        por_fila = {f["fila"]: f for f in self.filas}
        self.assertFalse(por_fila[3].get("descartada"))
        self.assertTrue(por_fila[5]["descartada"])
        self.assertIn("fila 3", por_fila[5]["motivo_descarte"])
        # La persona que no está repetida no se toca.
        self.assertFalse(por_fila[4].get("descartada"))

    def test_sin_eleccion_no_procesa(self):
        # El caso peligroso: sin esto se cargarían las dos matrículas, que es
        # justo lo que la decisión quiso evitar.
        with self.assertRaises(mod.CargueInvalido) as ctx:
            mod.aplicar_elecciones(self.filas, {})
        self.assertIn("Falta elegir", str(ctx.exception))

    def test_eleccion_que_apunta_a_otra_fila_no_pasa(self):
        with self.assertRaises(mod.CargueInvalido) as ctx:
            mod.aplicar_elecciones(self.filas, {"1": 4})   # la 4 es de otro doc
        self.assertIn("no es", str(ctx.exception))

    def test_acepta_la_eleccion_como_texto(self):
        # Llega por multipart dentro de un JSON: las claves y valores pueden
        # venir como strings.
        mod.aplicar_elecciones(self.filas, {"1": "5"})
        por_fila = {f["fila"]: f for f in self.filas}
        self.assertTrue(por_fila[3]["descartada"])
        self.assertFalse(por_fila[5].get("descartada"))

    def test_sin_repetidos_no_exige_nada(self):
        filas = [fila(3, "1"), fila(4, "2")]
        mod.aplicar_elecciones(filas, {})
        self.assertFalse(any(f.get("descartada") for f in filas))


class CargablesTests(unittest.TestCase):

    def test_excluye_errores_y_descartadas(self):
        filas = [fila(3, "1"), fila(4, "2", estado="error"),
                 fila(5, "3"), fila(6, "4")]
        filas[2]["descartada"] = True
        self.assertEqual([f["fila"] for f in mod._cargables(filas)], [3, 6])


class CamposAEscribirTests(unittest.TestCase):
    """Qué se escribe de verdad al actualizar. Dos reglas, dos daños evitados."""

    def _campos(self):
        return {"numero_documento": "1", "nombre1": "MARIA", "telefono": None,
                "correo": "", "programa_academico": "ADMINISTRACIÓN",
                "nivel_formacion": "profesional", "snies_ies": "1111",
                "cumplimiento_acceso": False, "cumplimiento_permanencia": False,
                "metas_codigos": None}

    def test_archivo_sin_cumplimiento_no_apaga_el_ya_marcado(self):
        # EL caso peligroso: las 174 entregas de 2025 quedaron en ACCESO por
        # decisión del área, no por el archivo. Un recargue cuyo archivo no
        # trae la columna NO puede ponerlas en False y borrar en silencio la
        # ejecución ya reportada de una meta.
        salida = mod.campos_a_escribir(self._campos(), trae_cumplimiento=False,
                                       es_actualizacion=True)
        for campo in mod.CAMPOS_CUMPLIMIENTO:
            self.assertNotIn(campo, salida)

    def test_archivo_con_cumplimiento_si_manda(self):
        campos = {**self._campos(), "cumplimiento_permanencia": True,
                  "metas_codigos": "23772"}
        salida = mod.campos_a_escribir(campos, trae_cumplimiento=True,
                                       es_actualizacion=True)
        self.assertTrue(salida["cumplimiento_permanencia"])
        self.assertEqual(salida["metas_codigos"], "23772")

    def test_al_actualizar_un_vacio_no_pisa_lo_que_hay(self):
        # El archivo oficial no trae teléfono ni correo. Si los mandara vacíos
        # sobre una fila que los tiene (los dejó el ciudadano en el QR), la
        # actualización sería una pérdida.
        salida = mod.campos_a_escribir(self._campos(), trae_cumplimiento=True,
                                       es_actualizacion=True)
        self.assertNotIn("telefono", salida)
        self.assertNotIn("correo", salida)
        self.assertIn("nombre1", salida)

    def test_al_crear_entran_todos(self):
        # Al crear no hay nada que perder: la fila no existe.
        salida = mod.campos_a_escribir(self._campos(), trae_cumplimiento=True,
                                       es_actualizacion=False)
        self.assertIn("telefono", salida)
        self.assertIn("correo", salida)

    def test_los_academicos_pasan_aunque_vengan_vacios(self):
        # Son del archivo: si el archivo dice que no hay, es que no hay.
        campos = {**self._campos(), "nivel_formacion": None, "snies_ies": None}
        salida = mod.campos_a_escribir(campos, trae_cumplimiento=True,
                                       es_actualizacion=True)
        self.assertIn("nivel_formacion", salida)
        self.assertIn("snies_ies", salida)


class HashTests(unittest.TestCase):

    def test_hash_estable_y_deja_el_puntero_al_inicio(self):
        import io
        datos = io.BytesIO(b"contenido de prueba")
        h1 = mod.sha256_de(datos)
        h2 = mod.sha256_de(datos)      # si no rebobinara, el segundo sería otro
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
        self.assertEqual(datos.read(), b"contenido de prueba")


if __name__ == "__main__":
    unittest.main()
