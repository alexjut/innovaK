"""El parser de obligaciones, contra textos que reproducen los casos medidos.

Estos tests no tocan la red ni la base: son el parser contra cadenas. Cada uno
reproduce un fallo REAL que costó un diagnóstico falso durante la construcción,
el 2026-10-15, sobre seis estudios previos descargados.

Ninguna cadena viene de un documento real: son reconstrucciones con texto
inventado que conservan solo la FORMA que causó el fallo. El repositorio es
público y un estudio previo trae nombres de contratistas.
"""
import unittest

from apps.presupuesto.services import obligaciones_pdf as O


class EncabezadoTests(unittest.TestCase):

    def test_no_confunde_la_mencion_en_prosa_con_el_encabezado(self):
        """El fallo: buscarlo como subcadena.

        La frase «…y las obligaciones específicas descritas…» aparece páginas
        antes de la sección, y arrancando ahí no hay ninguna lista que leer: el
        contrato quedaba como «sin lista numerada» teniendo sus 8 obligaciones.
        """
        texto = (
            "con el propósito de garantizar el objeto del contrato y las "
            "obligaciones específicas descritas, cumpliendo con la necesidad.\n"
            "2. OBJETO\n"
            "Prestar servicios.\n"
            "10.5 OBLIGACIONES ESPECÍFICAS\n"
            "1 . Primera obligación del contratista.\n"
            "2 . Segunda obligación del contratista.\n"
            "3 . Tercera obligación del contratista.\n"
            "4 . Cuarta obligación del contratista.\n"
            "5 . Las demás inherentes al objeto.\n"
            "10.6 OBLIGACIONES DE LA SECRETARÍA DISTRITAL DE GOBIERNO\n"
            "1 . Designar al supervisor.\n")
        enc, items, motivo = O.extraer(texto)
        self.assertIsNone(motivo)
        self.assertEqual([i["numero"] for i in items], [1, 2, 3, 4, 5])
        self.assertIn("Primera obligación", items[0]["descripcion"])

    def test_tolera_los_espacios_dobles_del_pdf(self):
        """El fallo: exigir un espacio entre palabras.

        Un documento trae `10.5 OBLIGACIONES  ESPECÍFICAS` con dos espacios
        —la extracción los mete— y quedaba como «sin sección» con la lista
        completa adentro.
        """
        texto = ("10.5 OBLIGACIONES  ESPECÍFICAS\n"
                 "1 . Una obligación.\n2 . Otra obligación.\n"
                 "3 . Una tercera.\n4 . Una cuarta.\n"
                 "5 . Las demás inherentes.\n"
                 "VALOR DEL CONTRATO\n")
        enc, items, motivo = O.extraer(texto)
        self.assertIsNone(motivo, f"no encontró la sección: {motivo}")
        self.assertEqual(len(items), 5)

    def test_sin_seccion_lo_dice(self):
        """Un convenio reparte compromisos entre las partes y no tiene esta
        sección. Eso es un hecho del documento, no un fallo del parser."""
        enc, items, motivo = O.extraer(
            "CLÁUSULAS\nPRIMERA. OBJETO\nSEGUNDA. VALOR\n")
        self.assertEqual(motivo, "sin_seccion")
        self.assertEqual(items, [])


class CierreDeLaListaTests(unittest.TestCase):

    def test_una_obligacion_no_se_corta_a_si_misma(self):
        """El fallo: «SUPERVISI» como cierre.

        La obligación 1 dice «siguiendo los lineamientos establecidos por el
        supervisor y/o apoyo a la supervisión», y la sección se cortaba ahí
        mismo: se publicaba 1 obligación de 5.
        """
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Gestionar lo asignado siguiendo los lineamientos "
                 "establecidos por el supervisor y/o apoyo a la supervisión\n"
                 "2 . Brindar atención oportuna.\n"
                 "3 . Organizar el archivo.\n4 . Hacer seguimiento.\n"
                 "5 . Las demás inherentes.\n"
                 "SUPERVISIÓN DEL CONTRATO\n"
                 "El supervisor será designado.\n")
        enc, items, motivo = O.extraer(texto)
        self.assertIsNone(motivo)
        self.assertEqual(len(items), 5, "la obligación 1 se cortó a sí misma")

    def test_una_obligacion_que_empieza_con_garantizar_no_cierra_la_lista(self):
        """El fallo: el número de lista valía como prefijo de encabezado.

        «3 . Garantizar técnicamente el proceso…» coincidía con el cierre
        `GARANT` y la lista se cortaba en el 2.
        """
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Una cosa.\n2 . Otra cosa.\n"
                 "3 . Garantizar técnicamente el proceso de clasificación.\n"
                 "4 . Hacer seguimiento al archivo.\n"
                 "5 . Las demás inherentes.\n"
                 "GARANTÍAS\n"
                 "El contratista constituirá póliza.\n")
        enc, items, motivo = O.extraer(texto)
        self.assertIsNone(motivo)
        self.assertEqual([i["numero"] for i in items], [1, 2, 3, 4, 5])

    def test_no_se_traga_la_lista_siguiente(self):
        """Los números van de 1 en 1: donde vuelve a empezar, termina.

        Sin esta regla, las obligaciones de la Secretaría se publicarían como
        obligaciones del contratista.
        """
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Del contratista una.\n2 . Del contratista dos.\n"
                 "3 . Del contratista tres.\n4 . Del contratista cuatro.\n"
                 "5 . Del contratista cinco.\n"
                 "ALGO QUE NO ESTÁ EN LA LISTA DE CIERRES\n"
                 "1 . De la entidad una.\n"
                 "2 . De la entidad dos.\n")
        enc, items, motivo = O.extraer(texto)
        self.assertEqual(len(items), 5,
                         "se tragó la lista de la entidad como si fuera del "
                         "contratista")
        self.assertIn("contratista", items[-1]["descripcion"])


class ListaIncompletaTests(unittest.TestCase):

    def test_una_lista_a_medias_NO_se_publica(self):
        """El caso más importante de todo el frente, en su forma medida.

        En un documento real, tras la obligación 5 sigue otra SIN número porque
        el PDF lo perdió, y después viene la sección 10.6. La lista tiene 8 y
        leeríamos 5. Publicar 5 de 8 en una certificación laboral es peor que no
        publicar ninguna: quien la lee no tiene forma de notar que faltan tres.
        """
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Primera.\n"
                 "2 . Segunda.\n"
                 "Sexta obligación que perdió su número y sigue en prosa "
                 "describiendo una actividad larga del contratista que ocupa "
                 "varias líneas del documento original, suficientes para que "
                 "no pase por una firma ni por un pie de página cualquiera.\n"
                 "10.6 OTRA COSA\n")
        enc, items, motivo = O.extraer(texto)
        self.assertEqual(motivo, "lista_incompleta")
        self.assertEqual(items, [],
                         "entregó una lista a medias: eso va impreso en un "
                         "certificado laboral")

    def test_la_continuacion_al_final_tambien_se_caza(self):
        """La misma trampa sin nada que la corte después.

        Ahí no sobra cola —la continuación se absorbe dentro de la última
        obligación, que queda desproporcionada—, así que la regla de la cola no
        alcanza y hace falta la del largo.
        """
        largo = ("Continuación sin número que describe una actividad del "
                 "contratista durante varias líneas seguidas. " * 9)
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Primera corta.\n"
                 "2 . Segunda corta.\n"
                 "3 . Tercera corta.\n"
                 "4 . Cuarta y " + largo + "\n")
        enc, items, motivo = O.extraer(texto)
        self.assertEqual(motivo, "lista_incompleta",
                         "la última obligación absorbió texto sin numerar y "
                         "pasó como lista completa")

    def test_una_cola_corta_no_la_invalida(self):
        """Un «Fin.» o una firma suelta no significan que falten obligaciones."""
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Primera.\n2 . Segunda.\n3 . Tercera.\n4 . Cuarta.\n"
                 "5 . Las demás inherentes al objeto.\n"
                 "   \n.\n")
        enc, items, motivo = O.extraer(texto)
        self.assertIsNone(motivo)
        self.assertEqual(len(items), 5)


class CalidadDelTextoTests(unittest.TestCase):

    def test_las_cinco_palabras_de_una_letra_no_cuentan_como_basura(self):
        """El fallo que casi descartó el frente entero.

        La primera métrica contaba TODAS las letras sueltas y daba 10 % en un
        texto limpio, lo que me llevó a concluir que el texto era inservible.
        528 de 668 eran «y», «a», «o», «e», «u», que son palabras del español.
        """
        limpio = ("El contratista y la entidad acuerdan a su vez o en su "
                  "defecto e incluso u otra cosa " * 6)
        self.assertLess(
            O.calidad_pct(limpio), 1.0,
            "las palabras de una letra del español están contando como texto "
            "roto")

    def test_el_texto_partido_sale_con_calidad_alta(self):
        """«verac idad», «docume ntos»: así vienen algunos PDF."""
        roto = "l a v e r a c i d a d d e l o s d o c u m e n t o s " * 8
        self.assertGreater(O.calidad_pct(roto), O.CALIDAD_MAXIMA_PCT)

    def test_un_texto_vacio_no_pasa_la_compuerta(self):
        self.assertEqual(O.calidad_pct(""), 100.0)


class SeccionCrudaTests(unittest.TestCase):

    def test_el_texto_de_la_seccion_se_puede_recuperar_aunque_no_haya_lista(self):
        """Es lo que permite transcribir a mano sin volver a buscar el PDF."""
        texto = ("Preámbulo.\n10.5 OBLIGACIONES ESPECÍFICAS\n"
                 "Un párrafo sin numerar que describe las obligaciones.\n")
        self.assertIsNone(O.extraer(texto)[1] or None)
        cruda = O.seccion_cruda(texto)
        self.assertIsNotNone(cruda)
        self.assertIn("OBLIGACIONES ESPECÍFICAS", cruda)
        self.assertNotIn("Preámbulo", cruda)

    def test_una_lista_de_dos_items_es_un_parseo_truncado(self):
        """Medido sobre 326 documentos: el mínimo real son 5 obligaciones.

        Ninguno tiene 3 o menos, así que una lista de dos no es una lista
        corta: es un parseo que se truncó. Las otras dos reglas no la ven —con
        dos ítems no hay mediana que comparar, y si la continuación se absorbe
        en el segundo no sobra cola—.
        """
        texto = ("OBLIGACIONES ESPECÍFICAS\n"
                 "1 . Primera.\n"
                 "2 . Segunda y después sigue en prosa sin numerar una "
                 "actividad larga del contratista.\n"
                 "10.6 OTRA COSA\n")
        enc, items, motivo = O.extraer(texto)
        self.assertEqual(motivo, "lista_incompleta")
        self.assertEqual(items, [])


class FalloDeConexionTests(unittest.TestCase):
    """Un fallo nuestro no se escribe como un fallo del documento.

    El 2026-10-15, corriendo sin pausa, SECOP nos bloqueó tras ~1.500 descargas
    y 379 documentos quedaron marcados «no se pudo descargar». Era falso: el
    que falló fuimos nosotros, y esos documentos estaban bien. Marcarlos así
    los habría dejado acusados para siempre, y la API habría publicado ese
    motivo como si fuera del documento.
    """

    def test_el_comando_distingue_conexion_de_http(self):
        """Un 404 habla del documento; un corte de TLS habla de nosotros."""
        from apps.presupuesto.management.commands import extraer_obligaciones as E
        self.assertTrue(hasattr(E, "PAUSA_S"))
        self.assertGreaterEqual(E.PAUSA_S, 1.0,
                                "sin pausa el origen vuelve a bloquearnos")
        self.assertTrue(hasattr(E, "MAX_FALLOS_SEGUIDOS"))
        self.assertLessEqual(
            E.MAX_FALLOS_SEGUIDOS, 20,
            "un freno que tolera decenas de fallos seguidos no frena nada")

    def test_un_fallo_de_conexion_se_nombra_como_tal(self):
        """El prefijo del motivo es lo que decide si el documento se acusa."""
        from unittest import mock

        from apps.presupuesto.management.commands import extraer_obligaciones as E
        with mock.patch.object(E.urllib.request, "urlopen",
                               side_effect=OSError("boom")):
            datos, motivo = E._descargar("https://example.invalid/x.pdf")
        self.assertIsNone(datos)
        self.assertTrue(motivo.startswith("conexion_"),
                        f"un fallo de conexión se nombró «{motivo}»: con ese "
                        "prefijo el documento queda marcado como fallido")

    def test_un_estado_http_si_habla_del_documento(self):
        from unittest import mock

        from apps.presupuesto.management.commands import extraer_obligaciones as E
        err = E.urllib.error.HTTPError("u", 404, "no está", {}, None)
        with mock.patch.object(E.urllib.request, "urlopen", side_effect=err):
            datos, motivo = E._descargar("https://example.invalid/x.pdf")
        self.assertEqual(motivo, "http_404")
