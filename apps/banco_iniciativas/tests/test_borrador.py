"""Tests del guardado progresivo del formulario público del Banco.

Mongo se simula: lo que se prueba acá es la lógica del token y de la vigencia,
que es donde está el riesgo. El endpoint es PÚBLICO y el borrador lleva cédulas
y direcciones adentro, así que un token débil es una fuga de datos personales,
no una molestia.

Datos INVENTADOS (repo público, habeas data).
"""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from apps.banco_iniciativas.services import borrador as b


class _MongoFalso:
    """Doble en memoria de `mongo_storage`, con la misma semántica."""

    def __init__(self):
        self.docs = {}
        self._n = 0

    def guardar(self, plaintext, mime, owner):
        self._n += 1
        oid = f"{self._n:024x}"
        self.docs[oid] = (bytes(plaintext), mime, owner)
        return oid

    def actualizar(self, mongo_id, plaintext, mime, owner=None):
        if mongo_id not in self.docs:
            return False
        self.docs[mongo_id] = (bytes(plaintext), mime,
                               owner or self.docs[mongo_id][2])
        return True

    def leer(self, mongo_id):
        if mongo_id not in self.docs:
            raise ValueError("no existe")
        crudo, mime, _ = self.docs[mongo_id]
        return crudo, mime

    def borrar(self, mongo_id):
        return self.docs.pop(mongo_id, None) is not None


class _BaseBorrador(unittest.TestCase):
    def setUp(self):
        self.mongo = _MongoFalso()
        parche = mock.patch.object(b, "mongo_storage", self.mongo)
        parche.start()
        self.addCleanup(parche.stop)


class TestGuardarYLeer(_BaseBorrador):

    def test_ida_y_vuelta(self):
        datos = {"rep_nombre": "NOMBRE DE PRUEBA", "tamano_staff_num": 12}
        res = b.guardar(62, datos)
        self.assertTrue(res["token"])
        self.assertEqual(b.leer(62, res["token"])["datos"], datos)

    def test_el_token_no_cambia_al_reguardar(self):
        """Si cambiara en cada autoguardado, una respuesta perdida dejaría al
        ciudadano con un token muerto y el borrador huérfano."""
        primero = b.guardar(62, {"paso": 1})
        segundo = b.guardar(62, {"paso": 2}, token=primero["token"])
        self.assertEqual(primero["token"], segundo["token"])
        self.assertEqual(b.leer(62, segundo["token"])["datos"], {"paso": 2})

    def test_reguardar_no_acumula_documentos(self):
        t = b.guardar(62, {"paso": 1})["token"]
        for i in range(2, 6):
            b.guardar(62, {"paso": i}, token=t)
        self.assertEqual(len(self.mongo.docs), 1)

    def test_token_valido_con_documento_purgado_crea_uno_nuevo(self):
        """Venció y lo purgó la limpieza: no se pierde lo que acaba de escribir."""
        t = b.guardar(62, {"paso": 1})["token"]
        self.mongo.docs.clear()
        nuevo = b.guardar(62, {"paso": 2}, token=t)
        self.assertNotEqual(nuevo["token"], t)
        self.assertEqual(b.leer(62, nuevo["token"])["datos"], {"paso": 2})

    def test_descartar_lo_borra(self):
        t = b.guardar(62, {"x": 1})["token"]
        self.assertTrue(b.descartar(t))
        self.assertEqual(self.mongo.docs, {})
        with self.assertRaises(b.BorradorInvalido):
            b.leer(62, t)

    def test_descartar_token_basura_no_revienta(self):
        self.assertFalse(b.descartar("cualquier-cosa"))
        self.assertFalse(b.descartar(""))


class TestSeguridadDelToken(_BaseBorrador):
    """El endpoint es público: el token es lo ÚNICO que protege los datos."""

    def test_el_id_de_mongo_pelado_no_abre_nada(self):
        """Los ObjectId son semi-secuenciales y se pueden enumerar; sin la
        firma, adivinar el id entregaría la cédula de otra persona."""
        b.guardar(62, {"rep_numero_doc": "000000000"})
        oid = next(iter(self.mongo.docs))
        with self.assertRaises(b.BorradorInvalido):
            b.leer(62, oid)

    def test_firma_alterada_no_abre(self):
        t = b.guardar(62, {"x": 1})["token"]
        oid, _, firma = t.partition(".")
        alterada = ("a" if firma[0] != "a" else "b") + firma[1:]
        with self.assertRaises(b.BorradorInvalido):
            b.leer(62, f"{oid}.{alterada}")

    def test_token_de_otro_evento_no_abre_este_formulario(self):
        t = b.guardar(62, {"x": 1})["token"]
        with self.assertRaises(b.BorradorInvalido):
            b.leer(93, t)

    def test_tokens_mal_formados(self):
        for malo in ("", "sinpunto", ".", ".firma", "id."):
            with self.subTest(token=malo):
                with self.assertRaises(b.BorradorInvalido):
                    b.leer(62, malo)


class TestVigencia(_BaseBorrador):

    def _vencer(self, token, dias):
        """Reescribe el sobre con una fecha de expiración en el pasado."""
        oid = token.partition(".")[0]
        crudo, mime, owner = self.mongo.docs[oid]
        sobre = json.loads(crudo.decode())
        sobre["expira_en"] = (
            datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        self.mongo.docs[oid] = (json.dumps(sobre).encode(), mime, owner)

    def test_borrador_vencido_no_se_lee(self):
        t = b.guardar(62, {"x": 1})["token"]
        self._vencer(t, 1)
        with self.assertRaises(b.BorradorInvalido):
            b.leer(62, t)

    def test_fecha_ilegible_se_trata_como_vencido(self):
        """Un error de formato no puede volver inmortal un borrador con
        cédulas adentro."""
        self.assertTrue(b._vencido({"expira_en": "no-es-una-fecha"}))

    def test_sin_fecha_no_vence(self):
        self.assertFalse(b._vencido({}))

    def test_manda_la_fecha_de_adentro_no_la_de_los_metadatos(self):
        """La fecha está en los dos lados y eso es deliberado: la de `owner`
        (en claro) existe solo para que la purga filtre sin descifrar. La que
        decide si se puede LEER es la de adentro. Si mandara la de afuera,
        revivir un borrador ajeno sería editar un campo de Mongo."""
        t = b.guardar(62, {"x": 1})["token"]
        oid = t.partition(".")[0]
        crudo, mime, owner = self.mongo.docs[oid]

        # Vence el de adentro y deja el de afuera en el futuro lejano.
        sobre = json.loads(crudo.decode())
        sobre["expira_en"] = (
            datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        owner = dict(owner, expira_en="2099-01-01T00:00:00+00:00")
        self.mongo.docs[oid] = (json.dumps(sobre).encode(), mime, owner)

        with self.assertRaises(b.BorradorInvalido):
            b.leer(62, t)


class TestLimites(_BaseBorrador):

    def test_payload_gigante_se_rechaza(self):
        with self.assertRaises(b.BorradorInvalido):
            b.guardar(62, {"basura": "x" * (b.MAX_BYTES + 1)})

    def test_datos_que_no_son_objeto_se_rechazan(self):
        for malo in ([1, 2], "texto", 42):
            with self.subTest(datos=malo):
                with self.assertRaises(b.BorradorInvalido):
                    b.guardar(62, malo)

    def test_el_borrador_no_guarda_metadatos_personales_en_claro(self):
        """`owner` va sin cifrar en Mongo: no puede llevar datos de la persona."""
        t = b.guardar(62, {"rep_numero_doc": "000000000",
                           "rep_nombre": "NOMBRE DE PRUEBA"})["token"]
        _crudo, _mime, owner = self.mongo.docs[t.partition(".")[0]]
        self.assertEqual(set(owner), {"tipo", "evento_id", "expira_en"})
        self.assertNotIn("000000000", json.dumps(owner))
        self.assertNotIn("NOMBRE DE PRUEBA", json.dumps(owner))
