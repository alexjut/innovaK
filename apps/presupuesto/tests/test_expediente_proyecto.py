"""Tests del EXPEDIENTE DEL PROYECTO — el explorador maestro/detalle.

Se apoya en datos reales de la BD externa compartida (sin fixtures, igual que
el resto de la suite). Cada test se salta solo si el dato que necesita no
está, en vez de fallar por algo que no es un defecto del código.

Lo que se protege acá no es "que responda 200". Son cuatro formas de mentir
que ya le costaron pantallas a este proyecto:

  · perder contratos por llegar a ellos por `cdp_id` (4 de 25) en vez de por
    la atribución real (24 de 25) — el defecto medido del endpoint viejo;
  · contar dos veces un contrato que aporta a varias metas (el 97 aporta a 3);
  · publicar un KPI ejecutado en 0 cuando lo cierto es que nadie reportó;
  · inventar la etapa contractual o el plan de pagos, que NO existen en la BD.

Y que la lista del panel izquierdo y el detalle del derecho digan la MISMA
cifra: si divergen, el usuario ve "al día" en la lista y "crítico" al hacer
clic, y deja de creerle al tablero.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
URL_LISTA = "/presupuesto/api/proyectos/expediente/"
URL_DETALLE = "/presupuesto/api/proyectos/%s/expediente/"

# Cifras MEDIDAS contra la BD el 2026-08-23 (mismo corte que el muro).
N_PROYECTOS = 12
N_CONTRATOS_ATRIBUIDOS = 24        # de 25; el huérfano se ve en el muro
N_METAS = 24
N_METAS_SIN_INDICADOR = 2
N_INDICADORES = 23
N_INDICADORES_CON_AVANCE = 6       # los otros 17 van en null, no en 0
# Deben coincidir clavadas con `muro_subgrupos`: es la misma plata leída dos
# veces. Si una de las dos cambia sola, hay un doble conteo o una pérdida.
#
# Re-medido el 2026-08-24 tras la precarga desde SECOP: subió $4.826.780.000
# porque los contratos 97 y 98 —los convenios grandes de Seguridad— tenían
# `valor` en NULL. El total del muro subió más ($6.098.959.188) porque incluye
# además al huérfano, que acá no se cuenta por definición.
COMPROMETIDO_ATRIBUIDO = 39_992_207_242.0    # antes 35_165_427_242
# Re-medido el 2026-08-26: +$398.498.702 de girado que trajo el cron de las
# 08:31 desde SECOP. El comprometido no se movió, lo que confirma que fueron
# PAGOS de contratos ya atribuidos y no contratos nuevos. La misma cifra
# aparece en `test_muro_subgrupos.ATRIBUIDO_GIR`, que es el punto: son dos
# servicios leyendo la misma plata y tienen que moverse juntos.
GIRADO_ATRIBUIDO = 3_928_425_043.0           # antes 3_529_926_341

# El proyecto que destapó el defecto: 15 contratos reales que el endpoint
# viejo no ve porque ninguno cuelga de un CDP.
PROY_CULTURA = 1
PROY_CULTURA_CONTRATOS = 15
PROY_CULTURA_COMPROMETIDO = 713_221_534.0

# Contrato que aporta a TRES metas del proyecto 2809: la prueba de que los
# punteros no duplican.
CONTRATO_MULTIMETA = 97
METAS_DEL_CONTRATO_97 = [21, 22, 23]

# Indicador con un avance REPORTADO en cero. No es lo mismo que no reportar,
# y el expediente tiene que poder distinguirlos.
INDICADOR_CERO_REPORTADO = 31


class ExpedienteProyectoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.anon = Client(HTTP_HOST=HOST)
        cls.auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.auth.force_login(cls.user)
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        cls.lista = expediente_lista()
        cls._detalle = expediente_proyecto
        cls.exps = [expediente_proyecto(p["id"]) for p in cls.lista["proyectos"]]

    @classmethod
    def _todas_las_metas(cls):
        return [m for e in cls.exps for m in e["metas"]]

    @classmethod
    def _todos_los_indicadores(cls):
        return [i for m in cls._todas_las_metas() for i in m["indicadores"]]

    def _proy(self, pid):
        return next((e for e in self.exps if e["id"] == pid), None)

    # ── Endpoints ──────────────────────────────────────────────────

    def test_las_dos_rutas_estan_registradas(self):
        self.assertEqual(reverse("presupuesto:api_proyectos_expediente"), URL_LISTA)
        self.assertEqual(reverse("presupuesto:api_proyecto_expediente", args=[1]),
                         URL_DETALLE % 1)

    def test_responden_200_autenticado(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.auth.get(URL_LISTA)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["n_proyectos"], N_PROYECTOS)
        pid = r.json()["proyectos"][0]["id"]
        self.assertEqual(self.auth.get(URL_DETALLE % pid).status_code, 200)

    def test_sin_auth_no_pasa(self):
        self.assertIn(self.anon.get(URL_LISTA).status_code, (301, 302, 401, 403))
        self.assertIn(self.anon.get(URL_DETALLE % 1).status_code, (301, 302, 401, 403))

    def test_un_proyecto_que_no_existe_da_404_no_500(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        self.assertEqual(self.auth.get(URL_DETALLE % 999999).status_code, 404)

    def test_el_endpoint_viejo_sigue_intacto(self):
        """`ProyectoDetailView` responde OTRA pregunta (el árbol CDP→contrato)
        y sigue sirviendo a /presupuesto/proyectos/<id>. Si este test se cae,
        es que el expediente le pisó la forma a una pantalla que no pidió nada."""
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.auth.get("/presupuesto/api/proyectos/%s/" % PROY_CULTURA)
        self.assertEqual(r.status_code, 200)
        self.assertIn("cdps", r.json())
        self.assertIn("presupuesto_total_cdps", r.json())

    # ── La lista es de PROYECTOS, no de áreas ──────────────────────

    def test_la_lista_es_de_proyectos_y_trae_los_dos_filtros(self):
        """El encargo es explícito: la unidad es el proyecto y los filtros
        Área→Subgrupo solo sirven para ENCONTRARLO. Si `area` o `subgrupo` no
        viajan por fila, el panel izquierdo no puede filtrar en cascada."""
        self.assertEqual(len(self.lista["proyectos"]), N_PROYECTOS)
        for p in self.lista["proyectos"]:
            self.assertIn("area", p)
            self.assertIn("subgrupo", p)
            self.assertIn("n_metas", p)
            self.assertIn("n_contratos", p)
            self.assertIn("semaforo", p)

    def test_los_proyectos_sin_area_planig_no_desaparecen(self):
        """3 de los 12 no tienen área del PLANIG. Filtrarlos fuera de la lista
        los volvería invisibles también para el buscador."""
        cob = self.lista["cobertura"]
        self.assertEqual(cob["con_area_planig"] + cob["sin_area_planig"], N_PROYECTOS)
        self.assertTrue(cob["sin_area_motivo"])

    def test_la_lista_y_el_detalle_dicen_la_misma_cifra(self):
        """Si el maestro resumiera por su cuenta, el usuario vería un semáforo
        en la lista y otro al hacer clic."""
        for fila in self.lista["proyectos"]:
            det = self._proy(fila["id"])
            self.assertIsNotNone(det, f"falta el detalle de {fila['codigo']}")
            for clave in ("n_metas", "n_contratos", "comprometido", "girado",
                          "avance_pct", "semaforo", "pct_girado"):
                self.assertEqual(fila[clave], det[clave],
                                 f"{fila['codigo']}: {clave} discrepa")

    # ── El defecto que obligó a este servicio ──────────────────────

    def test_los_contratos_llegan_por_la_atribucion_no_por_el_cdp(self):
        """El endpoint viejo llega a los contratos por `cdp_id`, y solo 4 de
        25 lo tienen: el proyecto de Cultura salía con CERO contratos teniendo
        15 por $713.221.534. El frontend no puede reagrupar lo que no le llega."""
        cultura = self._proy(PROY_CULTURA)
        if cultura is None:
            self.skipTest("El proyecto de Cultura no está en esta BD")
        self.assertEqual(cultura["n_contratos"], PROY_CULTURA_CONTRATOS)
        self.assertAlmostEqual(cultura["comprometido"], PROY_CULTURA_COMPROMETIDO,
                               places=2)
        self.assertEqual(len(cultura["contratos"]), PROY_CULTURA_CONTRATOS)
        sin_cdp = [c for c in cultura["contratos"] if c["cdp_id"] is None]
        self.assertEqual(len(sin_cdp), PROY_CULTURA_CONTRATOS,
                         "si alguno tuviera cdp_id, este test dejaría de probar nada")

    def test_la_union_de_las_dos_vias_atribuye_24_de_25(self):
        """`contrato_proyecto` da 20 y `contrato_actividad_plan` da 5. Usar una
        sola mandaría contratos reales a un cajón de huérfanos."""
        total = sum(e["n_contratos"] for e in self.exps)
        self.assertEqual(total, N_CONTRATOS_ATRIBUIDOS)
        vias = {c["via_atribucion"] for e in self.exps for c in e["contratos"]}
        self.assertEqual(vias, {"contrato_proyecto", "contrato_actividad_plan"})

    def test_ningun_contrato_cae_en_dos_proyectos(self):
        """Si uno cayera en dos, su plata se contaría dos veces en el ledger."""
        ids = [c["id"] for e in self.exps for c in e["contratos"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_la_plata_cuadra_con_el_muro(self):
        """Es la misma plata leída por dos servicios. Si divergen, uno de los
        dos está sumando de más o perdiendo un contrato."""
        comp = sum(e["comprometido"] for e in self.exps)
        gir = sum(e["girado"] or 0.0 for e in self.exps)
        self.assertAlmostEqual(comp, COMPROMETIDO_ATRIBUIDO, places=2)
        self.assertAlmostEqual(gir, GIRADO_ATRIBUIDO, places=2)

    # ── Metas: punteros, no anidamiento ────────────────────────────

    def test_las_metas_llevan_punteros_y_el_contrato_va_una_sola_vez(self):
        """El contrato 97 aporta a 3 metas del 2809. Anidado se pintaría 3
        veces y —peor— se sumaría 3 veces."""
        metas = [m for m in self._todas_las_metas()
                 if CONTRATO_MULTIMETA in m["contratos_ids"]]
        if not metas:
            self.skipTest("El contrato multi-meta no está en esta BD")
        self.assertEqual(sorted(m["meta_proyecto_id"] for m in metas),
                         METAS_DEL_CONTRATO_97)
        apariciones = [c for e in self.exps for c in e["contratos"]
                       if c["id"] == CONTRATO_MULTIMETA]
        self.assertEqual(len(apariciones), 1)

    def test_los_contratos_sin_meta_se_declaran_no_se_reparten(self):
        """19 de los 24 llegan por `contrato_proyecto`, que no pasa por ninguna
        meta. Repartirlos «proporcionalmente» sería inventar una atribución."""
        con_sueltos = [e for e in self.exps if e["contratos_sin_meta"]]
        self.assertTrue(con_sueltos)
        for e in con_sueltos:
            self.assertTrue(e["contratos_sin_meta_motivo"])
            for cid in e["contratos_sin_meta"]:
                self.assertIn(cid, [c["id"] for c in e["contratos"]])

    def test_las_metas_sin_indicador_no_desaparecen(self):
        """2 de las 24 no tienen KPI. Si el panel se agrupara por indicador en
        vez de por meta, se esfumarían de la pantalla."""
        metas = self._todas_las_metas()
        self.assertEqual(len(metas), N_METAS)
        sin_ind = [m for m in metas if not m["indicadores"]]
        self.assertEqual(len(sin_ind), N_METAS_SIN_INDICADOR)
        for m in sin_ind:
            self.assertTrue(m["sin_indicador_motivo"])
            self.assertIsNone(m["avance_pct"])

    def test_la_meta_viaja_con_su_id_no_solo_con_el_codigo(self):
        """`meta_codigo` no identifica la meta cuando la misma cuelga de dos
        proyectos: el frontend necesita `meta_proyecto_id` para no mezclarlas."""
        ids = [m["meta_proyecto_id"] for m in self._todas_las_metas()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))

    # ── El KPI ejecutado: null, NUNCA 0 ────────────────────────────

    def test_el_kpi_sin_avance_va_en_null_y_no_en_cero(self):
        """17 de 23 indicadores no tienen ni una fila de avance. Un 0 ahí se
        lee «no avanzó»; la verdad es «no se ha reportado», y son dos problemas
        distintos con dos arreglos distintos."""
        inds = self._todos_los_indicadores()
        self.assertEqual(len(inds), N_INDICADORES)
        sin_avance = [i for i in inds if i["n_aportes"] == 0]
        self.assertEqual(len(inds) - len(sin_avance), N_INDICADORES_CON_AVANCE)
        for i in sin_avance:
            self.assertIsNone(i["ejecutado"], f"KPI {i['id']} salió con 0 en vez de null")
            self.assertIsNone(i["pct"])
            self.assertTrue(i["sin_avance_motivo"])

    def test_un_cero_REPORTADO_si_sale_como_cero(self):
        """El indicador 31 tiene una fila de avance con magnitud 0. Ese sí es
        un 0 de verdad y tiene que distinguirse del silencio."""
        ind = next((i for i in self._todos_los_indicadores()
                    if i["id"] == INDICADOR_CERO_REPORTADO), None)
        if ind is None:
            self.skipTest("El indicador del 0 reportado no está en esta BD")
        self.assertEqual(ind["ejecutado"], 0.0)
        self.assertEqual(ind["n_aportes"], 1)
        self.assertIsNone(ind["sin_avance_motivo"])

    def test_el_avance_del_proyecto_va_vacio_si_nadie_reporto(self):
        for e in self.exps:
            if e["indicadores_con_avance"] == 0:
                self.assertIsNone(e["avance_pct"],
                                  f"{e['codigo']} publica un % sin ningún avance")

    # ── Lo que NO existe: forma congelada + motivo ─────────────────

    def test_la_etapa_no_se_inventa(self):
        """La etapa YA tiene dónde vivir (DDL 010, 2026-08-23): el catálogo
        `etapa_contrato` y `contrato.etapa_codigo`. Lo que este test protege
        dejó de ser la forma congelada y pasó a ser la regla de fondo, que no
        cambió: **un contrato sin etapa registrada no aparece en ninguna**.

        Antes se afirmaban cuatro etapas inventadas (planeacion/contratacion/
        ejecucion/liquidacion) que NO son las del alcalde; las de verdad son
        Formulación / Ejecución / Liquidación / Sancionatorio. El detalle del
        catálogo, el stepper y el endpoint que la registra se prueban en
        `test_expediente_contrato`.
        """
        for e in self.exps:
            etapas = e["etapas"]
            self.assertIn("sin_dato", etapas)
            # Todo contrato cae en exactamente un casillero: ni se pierde ni
            # se cuenta dos veces.
            self.assertEqual(sum(etapas.values()), e["n_contratos"])
            self.assertEqual(etapas["sin_dato"],
                             sum(1 for c in e["contratos"] if c["etapa"] is None))
            for c in e["contratos"]:
                if c["etapa"] is None:
                    self.assertTrue(c["etapa_motivo"])

    def test_el_plan_de_pagos_no_se_inventa(self):
        """El plan de pagos NO sale de `crp` (0 filas): sale del espejo
        `secop_plan_pago` que llena `ingest_secop_plan_pagos`.

        La regla que se protege es la misma de antes —no inventar trimestres—
        pero ahora tiene dos lados: si hay filas, salen del espejo; si no las
        hay, la lista va vacía CON su motivo. Una lista vacía y muda se leería
        como «este contrato no tiene pagos», que es una afirmación que nadie
        midió.
        """
        for e in self.exps:
            for c in e["contratos"]:
                self.assertIsInstance(c["plan_pago"], list)
                if c["plan_pago"]:
                    self.assertIsNone(c["plan_pago_motivo"])
                else:
                    self.assertTrue(c["plan_pago_motivo"])

    def test_el_gauge_tecnico_es_null_donde_no_hay_dato(self):
        """`contrato.ejecucion` está lleno en 4 de 25: los otros van en gris."""
        ctos = [c for e in self.exps for c in e["contratos"]]
        con_dato = [c for c in ctos if c["ejecucion"] is not None]
        self.assertLess(len(con_dato), len(ctos))
        for c in con_dato:
            self.assertIsInstance(c["ejecucion"], float)

    def test_localidad_y_estado_se_declaran_ausentes_no_se_omiten(self):
        """La UI tiene que poder decir POR QUÉ el campo está vacío."""
        for e in self.exps:
            self.assertIsNone(e["localidad"])
            self.assertTrue(e["localidad_motivo"])
            self.assertIsNone(e["estado"])
            self.assertTrue(e["estado_motivo"])

    # ── El semáforo: el silencio no se califica ────────────────────

    def test_un_proyecto_sin_con_que_calcular_nunca_sale_verde_ni_rojo(self):
        """Acusar de incumplir a quien nadie le cargó el dato es inventar un
        juicio; y darle verde premiaría el silencio."""
        for e in self.exps:
            sin_base = (e["n_contratos"] == 0
                        or not e["comprometido"]
                        or e["contratos_conciliados"] == 0)
            if sin_base:
                self.assertEqual(e["semaforo"], "incompleto",
                                 f"{e['codigo']}: {e['semaforo_motivo']}")
                self.assertIsNone(e["pct_girado"])

    def test_el_semaforo_siempre_explica_por_que(self):
        for e in self.exps:
            self.assertIn(e["semaforo"],
                          ("al_dia", "atrasado", "critico", "incompleto"))
            self.assertTrue(e["semaforo_motivo"])
            self.assertTrue(e["base_semaforo"])

    def test_el_girado_es_null_cuando_no_hay_de_donde_leerlo(self):
        """El girado NO sale de innovaK, sale del espejo SECOP. Sin ningún
        contrato conciliado, un 0.0 diría «no han girado» cuando lo único
        cierto es que no sabemos."""
        for e in self.exps:
            if e["contratos_conciliados"] == 0:
                self.assertIsNone(e["girado"], f"{e['codigo']} publica un girado inventado")
                self.assertIsNone(e["saldo_por_girar"])

    def test_el_saldo_por_girar_es_comprometido_menos_girado(self):
        for e in self.exps:
            if e["saldo_por_girar"] is not None:
                self.assertAlmostEqual(e["saldo_por_girar"],
                                       e["comprometido"] - (e["girado"] or 0.0),
                                       places=2)

    # ── Cabecera: los dos cortes ───────────────────────────────────

    def test_la_cabecera_trae_los_dos_cortes_y_la_ventana(self):
        """Son DOS y distintos (SDP va un mes atrás de SECOP): publicar uno
        solo haría que las cifras mintieran sobre su fecha."""
        cab = self.lista["cabecera"]
        self.assertIn("corte", cab)
        self.assertIn("corte_pdl_oficial", cab)
        self.assertIsNotNone(cab["ventana_pdl"]["pct_tiempo_transcurrido"])

    # ── El identificador canónico ──────────────────────────────────

    def test_el_identificador_canonico_es_id_y_no_el_codigo(self):
        """`id` y `codigo` NO son el mismo número, y confundirlos rompe el panel.

        El proyecto de código 2784 tiene id 2802; el de código 2780 tiene id 1.
        La lista muestra el CÓDIGO —es lo que la gente reconoce— pero el detalle
        se pide por ID. Si alguien pasa el código, responde 404 y la pantalla
        dice «no existe» sobre un proyecto que sí existe.

        Lo traicionero: en el proyecto 2788 los dos números coinciden, así que
        un bug de identificador se ve INTERMITENTE y se diagnostica mal. Este
        test lo fija: cada `id` de la lista abre su expediente, y un código que
        no coincide con ningún id NO abre nada.
        """
        distintos = [e for e in self.exps
                     if str(e["codigo"]).lstrip("0") != str(e["id"])]
        self.assertTrue(distintos, "Se esperaba al menos un proyecto con id != codigo")

        ids = {e["id"] for e in self.exps}
        for e in self.exps:
            self.assertEqual(self.auth.get(URL_DETALLE % e["id"]).status_code, 200,
                             f"el id {e['id']} ({e['codigo']}) no abre su expediente")

        for e in distintos:
            codigo = str(e["codigo"]).lstrip("0")
            if not codigo.isdigit() or int(codigo) in ids:
                continue  # el código coincide con OTRO id: no prueba nada
            self.assertEqual(self.auth.get(URL_DETALLE % codigo).status_code, 404,
                             f"el código {codigo} no debería abrir un expediente")

    def test_ningun_proyecto_se_repite_en_la_lista(self):
        """Un proyecto con varias metas o contratos sigue siendo UNA fila.

        El maestro agrupa por proyecto; las metas y los contratos son del
        detalle. Si el SQL de atribución perdiera el GROUP BY, un proyecto con
        3 metas aparecería 3 veces y el contador mentiría.
        """
        ids = [e["id"] for e in self.exps]
        self.assertEqual(len(ids), len(set(ids)), "hay proyectos duplicados en la lista")
