"""Tests del CONTRATO dentro del expediente: etapa, plata y plan de pagos.

Complementa a `test_expediente_proyecto`, que protege la capa PROYECTO → META.
Acá se protege lo que se agregó el 2026-08-23 y las formas de mentir que trae
cada cosa:

  · **La etapa contractual.** No se puede derivar de SECOP —de nuestros 25
    contratos, SECOP dice «Modificado» en 20, que significa que hubo otrosí y
    no una etapa— así que NULL tiene que significar «pendiente de registrar» y
    nunca «Ejecución». El test que importa no es que se guarde: es que un
    contrato sin registrar NO aparezca en ninguna etapa.
  · **La auditoría.** Registrar la etapa dos veces no puede duplicar nada, pero
    SÍ tiene que refrescar fecha y usuario. Sin eso no se sabe qué tan fresco
    está el dato ni quién respondió por él.
  · **El scope.** Alex fue explícito: «no permitas que cualquier usuario
    modifique información contractual». Tener el módulo deja VER el tablero de
    toda la localidad; no deja TOCAR el contrato de otra área.
  · **$0 real contra «sin dato».** La regla que Alex marcó como la más
    importante. Un contrato que no cruza con SECOP tiene el girado en null, no
    en 0, y por lo tanto tampoco tiene saldo.
  · **La resta prohibida.** `programado_PDL - comprometido_SECOP` ya se
    descartó una vez: son universos y cortes distintos. El saldo del contrato
    solo puede ser comprometido − girado, y los dos del MISMO contrato.
  · **Jerga técnica en pantalla.** Los nombres de tablas van a logs. El
    payload entero se barre buscando backticks, flechas y nombres de tabla.

Como el resto de la suite: contra la BD externa compartida, sin fixtures, y
cada test se salta solo si el dato que necesita no está. Los tests que
ESCRIBEN dejan el contrato como lo encontraron (try/finally).
"""
import json
import re
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.urls import reverse

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
URL_ETAPA = "/presupuesto/api/contratos/%s/etapa/"

#: Las etapas del catálogo, en su orden. Se afirman por NOMBRE y por ORDEN
#: porque el stepper se dibuja con `orden`: si alguien reordena el catálogo, la
#: pantalla cambia de significado sin que cambie una línea de código.
#:
#: Eran cuatro (DDL 010). El 2026-08-26 entró «En elaboración» con orden 0
#: (DDL 015): el contrato que el área ya está estructurando y todavía no está
#: en SECOP. Va ANTES de Formulación —es lo primero que ocurre— y por eso su
#: orden es 0 y no 5; el código 5 es solo el siguiente libre de la tabla.
#: Que orden y código no coincidan es justamente lo que estos tests vigilan.
ETAPAS_ESPERADAS = [(5, "En elaboración", 0),
                    (1, "Formulación", 1), (2, "Ejecución", 2),
                    (3, "Liquidación", 3), (4, "Sancionatorio", 4)]

#: Medido 2026-08-23 contra la BD y contra la API de SECOP.
N_CONTRATOS = 25

#: PISO, no igualdad. Estas dos cifras las mueve una fuente EXTERNA: el cron de
#: las 03:30 trae el plan de pagos de SECOP, y cada vez que el Distrito publica
#: los pagos de un contrato nuestro, suben. Congeladas como igualdad rompían el
#: test sin que nadie hubiera tocado el código —pasó el 2026-08-27, cuando el
#: cruce pasó de 20/154 a 21/155— y un test que se pone rojo solo se termina
#: ignorando. Lo que hay que proteger es que el puente EMPATE y no se infle,
#: no que empate un número exacto.
CONTRATOS_CON_PLAN_DE_PAGOS_MIN = 20  # medido 20 el 2026-08-23, 21 el 2026-08-27
FILAS_DE_PAGO_NUESTRAS_MIN = 154      # medido 154 el 2026-08-23, 155 el 2026-08-27

#: Lo que NUNCA puede viajar en un texto que se pinta.
JERGA = re.compile(r"`|->|→|\bSELECT \b|\bJOIN \b|\bDDL\b")
NOMBRES_DE_TABLA = ("contrato_actividad_plan", "actividad_plan", "meta_proyecto",
                    "presu_", "secop_plan_pago", "sdp_meta_oficial",
                    "contrato_proyecto", "forma_pago")
#: Claves que llevan un CÓDIGO (enum para el frontend) o un dato real de la
#: entidad, no una frase para leer. No se les exige castellano.
CLAVES_NO_NARRATIVAS = {
    "via_atribucion", "via_meta", "programado_origen_codigo", "base_semaforo",
    "nombre", "descripcion", "objeto", "codigo", "estado", "unidad",
    "numero_de_factura", "notas",
}


def _sql(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _tabla_existe(nombre):
    return _sql("SELECT to_regclass(%s)", [nombre])[0][0] is not None


class EtapaContratoTests(unittest.TestCase):
    """El catálogo, el modelo y lo que el expediente publica de la etapa."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        cls.lista = expediente_lista()
        cls.exps = [expediente_proyecto(p["id"]) for p in cls.lista["proyectos"]]
        cls.contratos = [c for e in cls.exps for c in e["contratos"]]

    def test_el_catalogo_tiene_las_etapas_esperadas_en_orden(self):
        filas = _sql("SELECT codigo, nombre, orden FROM etapa_contrato ORDER BY orden")
        self.assertEqual([tuple(f) for f in filas], ETAPAS_ESPERADAS)

    def test_el_modelo_django_mapea_el_catalogo(self):
        from apps.presupuesto.models import EtapaContrato
        self.assertEqual(
            list(EtapaContrato.objects.order_by("orden")
                 .values_list("codigo", "nombre", "orden")),
            ETAPAS_ESPERADAS)

    def test_en_elaboracion_va_antes_que_formulacion(self):
        """Su ORDEN es 0 aunque su CÓDIGO sea 5.

        El código es solo el siguiente libre de la tabla; el orden es lo que
        dibuja el stepper. Confundirlos pondría «En elaboración» al final, o
        sea después de liquidar el contrato.
        """
        filas = _sql("SELECT codigo, orden FROM etapa_contrato ORDER BY orden")
        self.assertEqual(filas[0][0], 5, "la primera etapa del stepper no es En elaboración")
        self.assertEqual(filas[0][1], 0)
        ordenes = [f[1] for f in filas]
        self.assertEqual(ordenes, sorted(set(ordenes)),
                         "hay dos etapas con el mismo orden: el stepper las "
                         "pintaría en un puesto no determinista")

    def test_el_orden_de_las_etapas_es_unico_en_la_base(self):
        """No basta con que hoy no haya repetidos: la BASE tiene que impedirlo.

        El test de arriba comprueba el estado; este comprueba la garantía. Sin
        la restricción, dos etapas con el mismo `orden` salen en un orden no
        determinista y el stepper intercambia dos nodos entre una carga y otra.

        Es DEFERRABLE a propósito: un `UPDATE ... SET orden = orden + 1` pasa
        por estados intermedios con duplicados, y un UNIQUE normal lo
        rechazaría — o sea, impediría justo la operación legítima sobre esta
        tabla. Diferida, se comprueba al hacer commit.
        """
        filas = _sql("""SELECT pg_get_constraintdef(oid) FROM pg_constraint
                        WHERE conrelid = 'public.etapa_contrato'::regclass
                          AND conname = 'etapa_contrato_orden_key'""")
        self.assertTrue(filas, "falta la restricción de orden único (DDL 017)")
        definicion = filas[0][0]
        self.assertIn("UNIQUE (orden)", definicion)
        self.assertIn("DEFERRABLE", definicion)

    def test_el_numero_de_contrato_admite_nulo(self):
        """Un contrato «en elaboración» todavía NO tiene número: se asigna al
        firmar. Si la columna fuera NOT NULL habría que inventarle uno
        provisional, y un número inventado sobre información contractual es
        justo lo que no puede pasar."""
        filas = _sql("""SELECT is_nullable FROM information_schema.columns
                        WHERE table_name = 'contrato'
                          AND column_name = 'contrato_numero'""")
        self.assertEqual(filas[0][0], "YES")

    def test_la_conciliacion_con_secop_ignora_los_que_no_tienen_numero(self):
        """Sin esto, un contrato en elaboración entraría al cruce con número
        NULL y empataría con cualquier cosa —o rompería la consulta—. La
        guarda ya existía; este test impide que alguien la quite al no ver
        para qué servía."""
        import inspect

        from apps.dashboard.services import kpis_presupuesto
        self.assertIn("contrato_numero IS NOT NULL",
                      inspect.getsource(kpis_presupuesto))

    def test_el_contrato_tiene_los_tres_campos_de_la_etapa(self):
        """Los tres, no solo la etapa: sin fecha ni autor no hay auditoría."""
        from apps.presupuesto.models.core import Contrato
        campos = {f.name for f in Contrato._meta.get_fields()}
        self.assertIn("etapa", campos)
        self.assertIn("etapa_fecha", campos)
        self.assertIn("etapa_usuario", campos)
        cols = {f.column for f in Contrato._meta.concrete_fields}
        self.assertIn("etapa_codigo", cols)
        self.assertIn("etapa_usuario_id", cols)

    def test_el_catalogo_completo_viaja_en_la_cabecera(self):
        """Aunque NINGÚN contrato tenga etapa: es lo que permite pintar el
        stepper apagado en vez de no pintar nada."""
        cat = self.lista["cabecera"]["etapas_catalogo"]
        self.assertEqual([(e["codigo"], e["nombre"], e["orden"]) for e in cat],
                         ETAPAS_ESPERADAS)

    def test_cada_contrato_publica_su_etapa_o_el_motivo(self):
        self.assertTrue(self.contratos, "no hay contratos atribuidos")
        for c in self.contratos:
            with self.subTest(contrato=c["id"]):
                self.assertIn("etapa", c)
                self.assertIn("etapa_fecha", c)
                self.assertIn("etapa_registrada_por", c)
                if c["etapa"] is None:
                    # Sin etapa, el motivo tiene que estar: un hueco mudo se
                    # lee como un cero.
                    self.assertTrue(c["etapa_motivo"])
                else:
                    self.assertIsNone(c["etapa_motivo"])
                    self.assertEqual(
                        set(c["etapa"]), {"codigo", "nombre", "orden"})

    def test_sin_registrar_no_se_asume_ninguna_etapa(self):
        """La trampa principal: repartir los contratos sin etapa en «Ejecución».

        Se comprueba contra la BD, no contra el payload: los contratos con
        `etapa_codigo IS NULL` tienen que salir TODOS en `sin_dato`.
        """
        sin_etapa_bd = _sql(
            "SELECT COUNT(*) FROM contrato WHERE etapa_codigo IS NULL")[0][0]
        if sin_etapa_bd == 0:
            self.skipTest("todos los contratos tienen etapa registrada")
        for e in self.exps:
            etapas = e["etapas"]
            atribuidos = e["n_contratos"]
            self.assertEqual(sum(etapas.values()), atribuidos,
                             "el conteo por etapa no cuadra con los contratos")
            sin_dato = etapas["sin_dato"]
            reales = sum(1 for c in e["contratos"] if c["etapa"] is None)
            self.assertEqual(sin_dato, reales)

    def test_sin_etapa_nadie_figura_como_quien_la_registro(self):
        for c in self.contratos:
            if c["etapa"] is None:
                with self.subTest(contrato=c["id"]):
                    self.assertIsNone(c["etapa_registrada_por"])
                    self.assertIsNone(c["etapa_fecha"])

    def test_el_motivo_de_la_etapa_no_nombra_ninguna_tabla(self):
        for c in self.contratos:
            if c["etapa_motivo"]:
                with self.subTest(contrato=c["id"]):
                    self.assertNotRegex(c["etapa_motivo"], JERGA)


class EtapaEndpointTests(unittest.TestCase):
    """El PATCH que registra la etapa: permisos, scope, idempotencia."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = get_user_model().objects.filter(is_superuser=True).first()
        cls.anon = Client(HTTP_HOST=HOST)
        cls.auth = Client(HTTP_HOST=HOST)
        if cls.admin is not None:
            cls.auth.force_login(cls.admin)
        fila = _sql("SELECT id FROM contrato ORDER BY id LIMIT 1")
        cls.contrato_id = fila[0][0] if fila else None

    def setUp(self):
        if self.admin is None or self.contrato_id is None:
            self.skipTest("hace falta un superusuario y al menos un contrato")
        # Estado previo, para devolverlo tal cual (la BD es compartida).
        self._previo = _sql(
            "SELECT etapa_codigo, etapa_fecha, etapa_usuario_id FROM contrato "
            "WHERE id=%s", [self.contrato_id])[0]

    def tearDown(self):
        with connection.cursor() as cur:
            cur.execute("UPDATE contrato SET etapa_codigo=%s, etapa_fecha=%s, "
                        "etapa_usuario_id=%s WHERE id=%s",
                        list(self._previo) + [self.contrato_id])

    def _patch(self, cliente, contrato_id, cuerpo):
        return cliente.patch(URL_ETAPA % contrato_id, data=json.dumps(cuerpo),
                             content_type="application/json")

    def test_la_ruta_esta_registrada(self):
        self.assertEqual(
            reverse("presupuesto:api_contrato_etapa",
                    kwargs={"contrato_id": self.contrato_id}),
            URL_ETAPA % self.contrato_id)

    def test_anonimo_no_puede_leer_ni_escribir(self):
        self.assertIn(self.anon.get(URL_ETAPA % self.contrato_id).status_code,
                      (401, 403))
        self.assertIn(self._patch(self.anon, self.contrato_id,
                                  {"etapa_codigo": 2}).status_code, (401, 403))

    def test_registra_la_etapa_con_fecha_y_autor(self):
        r = self._patch(self.auth, self.contrato_id, {"etapa_codigo": 3})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["etapa"]["codigo"], 3)
        self.assertEqual(d["etapa"]["nombre"], "Liquidación")
        # Sin estas dos no hay auditoría, que es la mitad del punto del dato.
        self.assertTrue(d["etapa_fecha"])
        self.assertEqual(d["etapa_registrada_por"]["id"], self.admin.pk)
        cod, fecha, uid = _sql(
            "SELECT etapa_codigo, etapa_fecha, etapa_usuario_id FROM contrato "
            "WHERE id=%s", [self.contrato_id])[0]
        self.assertEqual((cod, uid), (3, self.admin.pk))
        self.assertIsNotNone(fecha)

    def test_registrar_dos_veces_no_duplica_pero_refresca_la_auditoria(self):
        primera = self._patch(self.auth, self.contrato_id, {"etapa_codigo": 2}).json()
        segunda = self._patch(self.auth, self.contrato_id, {"etapa_codigo": 2}).json()
        # Idempotente en el DATO...
        self.assertEqual(primera["etapa"], segunda["etapa"])
        self.assertEqual(
            _sql("SELECT COUNT(*) FROM contrato WHERE id=%s AND etapa_codigo=2",
                 [self.contrato_id])[0][0], 1)
        # ...pero la última confirmación es la que vale para saber qué tan
        # fresco está: la fecha SÍ se mueve.
        self.assertGreater(segunda["etapa_fecha"], primera["etapa_fecha"])

    def test_se_puede_corregir_borrando_la_etapa(self):
        self._patch(self.auth, self.contrato_id, {"etapa_codigo": 4})
        r = self._patch(self.auth, self.contrato_id, {"etapa_codigo": None})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertIsNone(d["etapa"])
        self.assertTrue(d["etapa_motivo"])
        # Al borrar NO puede quedar «pendiente de registrar, registrada por X»:
        # sería una contradicción en la misma tarjeta. La auditoría de quién
        # borró y cuándo se queda en la BD, que es donde sirve.
        self.assertIsNone(d["etapa_fecha"])
        self.assertIsNone(d["etapa_registrada_por"])
        _cod, fecha, uid = _sql(
            "SELECT etapa_codigo, etapa_fecha, etapa_usuario_id FROM contrato "
            "WHERE id=%s", [self.contrato_id])[0]
        self.assertIsNotNone(fecha, "el borrado tiene que quedar auditado en BD")
        self.assertEqual(uid, self.admin.pk)

    def test_una_etapa_inventada_se_rechaza(self):
        for basura in (99, 0, "Ejecución", "abc"):
            with self.subTest(valor=basura):
                r = self._patch(self.auth, self.contrato_id, {"etapa_codigo": basura})
                self.assertEqual(r.status_code, 400)
        # Un rechazo no puede dejar rastro: la etapa sigue como estaba.
        self.assertEqual(
            _sql("SELECT etapa_codigo FROM contrato WHERE id=%s",
                 [self.contrato_id])[0][0], self._previo[0])

    def test_sin_el_campo_no_adivina(self):
        self.assertEqual(self._patch(self.auth, self.contrato_id, {}).status_code, 400)

    def test_contrato_inexistente_da_404(self):
        self.assertEqual(
            self._patch(self.auth, 99_999_999, {"etapa_codigo": 1}).status_code, 404)

    def test_no_se_puede_tocar_el_contrato_de_otra_area(self):
        """El scope que pidió Alex, probado con un usuario real de la BD.

        Se busca un no-superusuario que TENGA el módulo (o sea, que pase el
        primer candado) y cuyo subgrupo NO cubra algún contrato. Si ese
        usuario logra escribir, el segundo candado no existe.
        """
        from apps.login.services.permisos import superusuario_o_modulo
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.services.expediente_proyecto import subgrupos_de_contrato

        ids = [f[0] for f in _sql("SELECT id FROM contrato ORDER BY id")]
        for u in get_user_model().objects.filter(is_superuser=False, is_active=True):
            visibles = subgrupos_visibles(u)
            if not visibles or not superusuario_o_modulo(u, "presupuesto_proyectos"):
                continue
            ajeno = next((cid for cid in ids
                          if (sg := subgrupos_de_contrato(cid)) and not (sg & visibles)),
                         None)
            if ajeno is None:
                continue
            cli = Client(HTTP_HOST=HOST)
            cli.force_login(u)
            r = self._patch(cli, ajeno, {"etapa_codigo": 2})
            self.assertEqual(r.status_code, 403, "un usuario de otra área escribió")
            self.assertNotRegex(r.json()["detail"], JERGA)
            self.assertIsNone(
                _sql("SELECT etapa_codigo FROM contrato WHERE id=%s", [ajeno])[0][0])
            return
        self.skipTest("no hay un usuario no-superuser con el módulo y scope propio")


class EjecucionPresupuestalContratoTests(unittest.TestCase):
    """La plata POR CONTRATO: $0 real contra «sin dato», y la resta prohibida."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        lista = expediente_lista()
        cls.exps = [expediente_proyecto(p["id"]) for p in lista["proyectos"]]
        cls.contratos = [c for e in cls.exps for c in e["contratos"]]

    def test_cada_contrato_trae_su_ejecucion_presupuestal(self):
        self.assertTrue(self.contratos)
        for c in self.contratos:
            with self.subTest(contrato=c["id"]):
                ep = c["ejecucion_presupuestal"]
                for k in ("programado", "comprometido", "girado", "saldo"):
                    self.assertIn(k, ep)

    def test_sin_dato_va_en_null_y_nunca_en_cero(self):
        """La regla que Alex marcó como la más importante.

        Si el contrato no cruza con SECOP no hay de dónde leer el girado: eso
        es «no sabemos», no «giraron $0». Y cada null viaja con su motivo, para
        que la pantalla pueda decir por qué está vacío.
        """
        for c in self.contratos:
            ep = c["ejecucion_presupuestal"]
            with self.subTest(contrato=c["id"]):
                if not c["conciliado_secop"]:
                    self.assertIsNone(ep["girado"])
                    self.assertTrue(ep["girado_motivo"])
                    # Sin girado no hay saldo: restarle a lo comprometido un
                    # cero inventado daría «falta girar todo», que es una
                    # afirmación que nadie midió.
                    self.assertIsNone(ep["saldo"])
                if c["valor"] is None:
                    self.assertIsNone(ep["comprometido"])
                    self.assertTrue(ep["comprometido_motivo"])
                    self.assertIsNone(ep["saldo"])
                if ep["programado"] is None:
                    self.assertTrue(ep["programado_motivo"])

    def test_el_programado_distingue_sin_cdp_de_cdp_sin_valor(self):
        """Dos huecos distintos que se veían iguales (los dos en null).

        Medido 2026-08-23: 4 contratos tienen `cdp_id` y los CDP a los que
        apuntan traen `valor` NULL; los otros 20 ni siquiera tienen CDP. Se
        arreglan distinto —uno es asociar el CDP, el otro cargarle el valor— y
        si los dos dijeran lo mismo, la pantalla le pediría al funcionario la
        tarea equivocada.
        """
        motivos = {c["ejecucion_presupuestal"]["programado_motivo"]
                   for c in self.contratos
                   if c["ejecucion_presupuestal"]["programado"] is None}
        self.assertTrue(motivos, "ningún contrato sin programado")
        for m in motivos:
            self.assertNotRegex(m, JERGA)
        con_cdp = [c for c in self.contratos if c["cdp_id"] is not None
                   and c["ejecucion_presupuestal"]["programado"] is None]
        for c in con_cdp:
            with self.subTest(contrato=c["id"]):
                self.assertIn("CDP", c["ejecucion_presupuestal"]["programado_motivo"])
                self.assertIn("valor", c["ejecucion_presupuestal"]["programado_motivo"])

    def test_el_saldo_es_comprometido_menos_girado_del_mismo_contrato(self):
        vistos = 0
        for c in self.contratos:
            ep = c["ejecucion_presupuestal"]
            if ep["saldo"] is None:
                continue
            vistos += 1
            with self.subTest(contrato=c["id"]):
                self.assertIsNotNone(ep["comprometido"])
                self.assertIsNotNone(ep["girado"])
                self.assertAlmostEqual(ep["saldo"],
                                       ep["comprometido"] - ep["girado"], places=2)
                self.assertEqual(ep["saldo_formula"], "comprometido - girado")
        self.assertGreater(vistos, 0, "ningún contrato pudo calcular saldo")

    def test_el_saldo_NO_es_programado_menos_comprometido(self):
        """La resta prohibida, que ya se descartó una vez y está documentada.

        `programado` sale del CDP y `comprometido` del contrato; mezclarlos con
        el programado del PDL sería cruzar universos y cortes distintos. El
        peligro es que el resultado PARECE una cifra sensata.
        """
        for c in self.contratos:
            ep = c["ejecucion_presupuestal"]
            if None in (ep["saldo"], ep["programado"], ep["comprometido"]):
                continue
            prohibido = ep["programado"] - ep["comprometido"]
            if abs(prohibido - (ep["comprometido"] - (ep["girado"] or 0))) < 0.01:
                continue      # coincidencia numérica, no la fórmula mala
            with self.subTest(contrato=c["id"]):
                self.assertNotAlmostEqual(ep["saldo"], prohibido, places=2)

    def test_el_girado_del_contrato_suma_el_del_proyecto(self):
        """La cifra del contrato y la del proyecto no pueden discrepar: son la
        misma plata leída dos veces."""
        for e in self.exps:
            if e["girado"] is None:
                continue
            suma = sum(c["ejecucion_presupuestal"]["girado"] or 0
                       for c in e["contratos"])
            with self.subTest(proyecto=e["id"]):
                self.assertAlmostEqual(e["girado"], suma, places=2)


class PlanDePagosTests(unittest.TestCase):
    """El plan de pagos: el parser, el espejo y el vacío con su causa."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        lista = expediente_lista()
        cls.exps = [expediente_proyecto(p["id"]) for p in lista["proyectos"]]
        cls.contratos = [c for e in cls.exps for c in e["contratos"]]

    # ── El parser, que es lo único testeable sin red ──────────────────

    def test_el_parser_tolera_punto_y_guion(self):
        """Las 62 formas de escribir una referencia. `CPS-033.2023` con PUNTO y
        `CPS-1113-2024` con GUION conviven en el mismo recurso de SECOP; un
        parser que solo acepte guion pierde la mitad."""
        from apps.presupuesto.management.commands.ingest_secop_plan_pagos import (
            parsear_referencia,
        )
        casos = {
            "CPS-033.2023": ("CPS", 33, 2023),      # punto, con ceros de relleno
            "CPS-1113-2024": ("CPS", 1113, 2024),   # guion
            "CAR-286-2021": ("CAR", 286, 2021),
            "cps-007.2022": ("CPS", 7, 2022),       # minúsculas
            "CPS - 45 - 2024": ("CPS", 45, 2024),   # espacios sueltos
            "CPS.99.2020": ("CPS", 99, 2020),       # punto en las dos posiciones
        }
        for ref, esperado in casos.items():
            with self.subTest(ref=ref):
                self.assertEqual(parsear_referencia(ref), esperado)

    def test_lo_que_no_parsea_se_cuenta_y_no_se_inventa(self):
        """Nunca se adivina una referencia: se devuelve la tripleta vacía para
        que la fila se guarde con los `ref_*` en NULL y se pueda CONTAR."""
        from apps.presupuesto.management.commands.ingest_secop_plan_pagos import (
            parsear_referencia,
        )
        for ref in ("054-2024", "CONTRATO DE ARRENDAMIENTO", "CO1.PCCNTR.4471720",
                    "", None, "###-####"):
            with self.subTest(ref=ref):
                self.assertEqual(parsear_referencia(ref), (None, None, None))

    def test_la_secuencia_desempata_sin_perder_ni_duplicar(self):
        """SECOP publica 4 pagos dos veces con la misma pareja (contrato, pago).

        Quedarse con uno perdería un dato real de la fuente; sumar los dos
        duplicaría la plata. Se guardan los dos, numerados, y solo el 0 suma.
        Además la numeración depende del CONTENIDO, no del orden en que la API
        los devuelva: si dependiera del orden, una re-ingesta reasignaría las
        secuencias y el UPSERT dejaría de ser idempotente.
        """
        from apps.presupuesto.management.commands.ingest_secop_plan_pagos import (
            numerar_duplicados,
        )
        def fila(pago, valor):
            return {"id_del_contrato": "X1", "id_de_pago": pago,
                    "valor_a_pagar": valor, "estado": "Pagado"}
        original = [fila("7", 100), fila("7", 200), fila("8", 300)]
        numerar_duplicados(original)
        self.assertEqual(sorted(f["secuencia"] for f in original if f["id_de_pago"] == "7"),
                         [0, 1])
        self.assertEqual([f["secuencia"] for f in original if f["id_de_pago"] == "8"], [0])
        # El mismo lote al revés reparte las MISMAS secuencias.
        alreves = [fila("7", 200), fila("7", 100), fila("8", 300)]
        numerar_duplicados(alreves)
        por_valor = {f["valor_a_pagar"]: f["secuencia"] for f in original}
        self.assertEqual({f["valor_a_pagar"]: f["secuencia"] for f in alreves},
                         por_valor)

    # ── El espejo y lo que publica el expediente ──────────────────────

    def test_el_expediente_no_revienta_sin_la_tabla(self):
        """Mientras el DDL 011 no esté aplicado, el plan va vacío CON su motivo.

        Es el requisito explícito: la pantalla no puede caerse porque falte una
        tabla que todavía nadie aprobó.
        """
        for c in self.contratos:
            with self.subTest(contrato=c["id"]):
                self.assertIsInstance(c["plan_pago"], list)
                if not c["plan_pago"]:
                    self.assertTrue(c["plan_pago_motivo"],
                                    "un plan vacío sin motivo se lee como «no hay pagos»")
                    self.assertNotRegex(c["plan_pago_motivo"], JERGA)
                else:
                    self.assertIsNone(c["plan_pago_motivo"])

    def test_cada_renglon_del_plan_distingue_programado_de_pagado(self):
        if not _tabla_existe("secop_plan_pago"):
            self.skipTest("el DDL 011 todavía no está aplicado")
        filas = [f for c in self.contratos for f in c["plan_pago"]]
        if not filas:
            self.skipTest("el espejo está vacío: falta correr la ingesta")
        for f in filas:
            with self.subTest(pago=f["id_pago"]):
                self.assertIn("programado", f)
                # `pagado` en null (no en 0) mientras no haya fecha REAL de
                # pago: un pago «Enviado Por Proveedor» todavía no se giró.
                if f["pagado"] is not None:
                    self.assertTrue(f["fecha_real"])
                    self.assertEqual((f["estado"] or "").lower(), "pagado")

    def test_el_espejo_cruza_con_nuestros_contratos(self):
        """El puente empata y no se infla. Las cifras son un PISO, no una foto.

        Se comprueban tres propiedades y ninguna cifra exacta:

        1. **Empata algo.** Un 0 acá sería el JOIN vacío que este proyecto ya
           sufrió: el que comparaba el número pelado contra la referencia
           completa y daba 0 de 25 durante meses.
        2. **No se infla.** Nunca puede cruzar más contratos de los que
           tenemos: si pasa, el JOIN está multiplicando filas.
        3. **No retrocede** por debajo de lo ya medido. SECOP publica, no
           despublica.
        """
        if not _tabla_existe("secop_plan_pago"):
            self.skipTest("el DDL 011 todavía no está aplicado")
        if not _sql("SELECT COUNT(*) FROM secop_plan_pago")[0][0]:
            self.skipTest("el espejo está vacío: falta correr la ingesta")
        contratos, filas = _sql("""
            SELECT COUNT(DISTINCT ct.id), COUNT(*)
            FROM contrato ct
            JOIN secop_plan_pago pp ON pp.ref_numero = ct.contrato_numero
                                   AND pp.ref_vigencia = ct.contrato_vigencia
            WHERE pp.secuencia = 0
        """)[0]
        self.assertGreater(contratos, 0,
                           "el espejo no cruza con ningún contrato: JOIN vacío")
        self.assertLessEqual(contratos, N_CONTRATOS,
                             f"cruzan {contratos} contratos y solo tenemos "
                             f"{N_CONTRATOS}: el JOIN está inflando filas")
        self.assertGreaterEqual(contratos, CONTRATOS_CON_PLAN_DE_PAGOS_MIN,
                                "el cruce RETROCEDIÓ respecto a lo medido: "
                                "SECOP publica, no despublica")
        self.assertGreaterEqual(filas, FILAS_DE_PAGO_NUESTRAS_MIN)
        self.assertGreaterEqual(filas, contratos,
                                "un contrato con plan de pagos tiene al menos "
                                "una fila")

    def test_el_espejo_no_tiene_claves_repetidas(self):
        """La unicidad (contrato, pago, secuencia) es lo que hace idempotente
        al UPSERT. Si se rompe, una re-ingesta empieza a duplicar plata."""
        if not _tabla_existe("secop_plan_pago"):
            self.skipTest("el DDL 011 todavía no está aplicado")
        repetidas = _sql("""
            SELECT COUNT(*) FROM (
                SELECT 1 FROM secop_plan_pago
                GROUP BY id_del_contrato, id_de_pago, secuencia HAVING COUNT(*) > 1
            ) x
        """)[0][0]
        self.assertEqual(repetidas, 0)

    def test_el_plan_de_pagos_no_se_escribio_en_crp(self):
        """`crp` es la vía INTERNA de Hacienda. Si la ingesta externa aterrizara
        ahí, nadie podría volver a distinguir un dato propio de uno bajado de
        internet."""
        if not _tabla_existe("crp"):
            self.skipTest("la tabla `crp` no existe")
        self.assertEqual(_sql("SELECT COUNT(*) FROM crp")[0][0], 0)


class SinJergaTecnicaTests(unittest.TestCase):
    """Barrido del payload COMPLETO buscando textos de desarrollador.

    Alex los señaló textualmente: `contrato_actividad_plan -> actividad_plan ->
    indicador -> meta` y «La tabla `proyecto` no tiene columna de localidad».
    Este test es la red para que no vuelvan a colarse por otro campo.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        cls.lista = expediente_lista()
        cls.exps = [expediente_proyecto(p["id"]) for p in cls.lista["proyectos"]]

    def _sospechosos(self, obj, ruta="", clave=None):
        malos = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                malos += self._sospechosos(v, f"{ruta}.{k}", k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                malos += self._sospechosos(v, f"{ruta}[{i}]", clave)
        elif isinstance(obj, str) and clave not in CLAVES_NO_NARRATIVAS:
            if JERGA.search(obj) or any(t in obj for t in NOMBRES_DE_TABLA):
                malos.append((ruta, obj))
        return malos

    def test_el_payload_no_muestra_nombres_de_tabla(self):
        malos = self._sospechosos(self.lista, "lista")
        for e in self.exps:
            malos += self._sospechosos(e, f"expediente[{e['id']}]")
        self.assertEqual(malos, [], f"jerga técnica en pantalla: {malos[:5]}")

    def test_la_localidad_sin_dato_se_dice_sin_dato(self):
        for e in self.exps:
            with self.subTest(proyecto=e["id"]):
                if e["localidad"] is None:
                    self.assertEqual(e["localidad_motivo"], "Sin dato")

    def test_los_contratos_sueltos_se_explican_en_castellano(self):
        """Los dos textos que dictó Alex, cada uno en su sitio: el de la meta
        que se quedó sin contratos y el del proyecto que los tiene sueltos."""
        vistos_meta = vistos_proyecto = 0
        for e in self.exps:
            if e["contratos_sin_meta"]:
                vistos_proyecto += 1
                self.assertIn("sección Contratos", e["contratos_sin_meta_motivo"])
                self.assertNotRegex(e["contratos_sin_meta_motivo"], JERGA)
            for m in e["metas"]:
                if not m["contratos_ids"]:
                    vistos_meta += 1
                    self.assertEqual(
                        m["sin_contratos_motivo"],
                        "No hay contratos asociados directamente a esta meta.")
        self.assertGreater(vistos_meta, 0)
        self.assertGreater(vistos_proyecto, 0)

    def test_el_kpi_sin_avance_no_cita_la_tabla_de_avances(self):
        for e in self.exps:
            for m in e["metas"]:
                for i in m["indicadores"]:
                    if i["ejecutado"] is None:
                        with self.subTest(indicador=i["id"]):
                            self.assertEqual(i["sin_avance_motivo"],
                                             "Sin avance reportado.")
