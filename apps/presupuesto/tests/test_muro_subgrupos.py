"""Tests del MURO de subgrupos.

Se apoya en datos reales de la BD externa compartida (sin fixtures, igual que
el resto de la suite). Cada test se salta solo si el dato que necesita no
está, en vez de fallar por algo que no es un defecto del código.

Lo que se protege acá NO es "que responda 200". Es que las tres formas de
mentir que ya le costaron tableros a este proyecto no vuelvan:

  · sumar un `total_programado` replicado 10 veces y publicar $6,6 billones;
  · cruzar códigos sin quitar ceros a la izquierda y publicar "0 cargados";
  · inflar el denominador del avance con un LEFT JOIN que se abre por fila.

Y que el silencio no se califique: un subgrupo sin datos no puede salir ni
verde ni rojo.
"""
import datetime as _dt
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
URL = "/presupuesto/api/muro-subgrupos/"

# Cifras MEDIDAS contra la BD. Re-medidas el 2026-08-24 tras la PRECARGA desde
# SECOP (`precargar_contratos_secop`), que subió el comprometido en
# **$6.098.959.188**. No es plata nueva: es plata que ya estaba contratada y
# era invisible porque `Contrato.valor` estaba en NULL. Tres contratos:
#
#     98 · CPS 1001/2025   $2.535.280.000
#     97 · CPS  983/2025   $2.291.500.000
#      1 · CPS 1113/2024   $1.272.179.188   ← el huérfano
#     ─────────────────────────────────────
#                          $6.098.959.188
#
# Las cifras viejas (comprometido 35.165.427.242, huérfanos $0) se dejan abajo
# a propósito: son la foto de ANTES de agotar la fuente, y explican por qué el
# tablero mostraba menos plata de la que había.
# El número de subgrupos NO se escribe acá. Estuvo en 45 hasta que alguien creó
# «Innovación» el 2026-08-26 y el test se puso rojo por un dato correcto: la
# organización creció. Un test que se rompe cuando el sistema hace bien su
# trabajo entrena a la gente a editar el test sin leerlo, que es como se pierde
# la vigilancia real.
#
# Lo que sí hay que proteger es el LEFT JOIN, y eso no se protege con un número
# fijo sino con la relación: TODOS los subgrupos salen, no solo los que tienen
# datos. Se afirma abajo comparando contra la tabla.
N_CONTRATOS = 25
COMPROMETIDO = 41_264_386_430.0      # antes 35_165_427_242
# Re-medido el 2026-08-26: el girado subió **$398.498.702** respecto al
# 2026-08-24. No es un defecto del código: el cron de las 08:31 trajo pagos
# nuevos de SECOP. Se ve en que el aumento es EL MISMO en el ledger y en la
# suma de las tarjetas, y el huérfano no se movió — o sea, entró por un
# contrato ya atribuido, no por uno nuevo.
GIRADO = 4_769_318_038.0             # antes 4_370_819_336
PROGRAMADO = 667_578_460_000.0
# El huérfano sigue siendo UNO y sigue siendo el mismo (contrato 1, CPS
# 1113/2024): no cuelga de ningún proyecto ni actividad. Lo que cambió es que
# ahora SÍ aporta al comprometido. El comentario viejo decía que aportaba $0
# «porque tiene girado en SECOP pero valor NULL en innovaK» — exactamente el
# hueco que la precarga cerró.
HUERFANOS_N, HUERFANOS_COMP, HUERFANOS_GIR = 1, 1_272_179_188.0, 840_892_995.0
ATRIBUIDO_COMP, ATRIBUIDO_GIR = 39_992_207_242.0, 3_928_425_043.0  # gir. antes 3_529_926_341
VINCULADOS = 24  # de 25, por la unión de las dos vías (antes 20 por una sola)


def _subgrupos_en_bd() -> int:
    """Cuántos subgrupos hay AHORA. La organización crece; el test no debería
    romperse por eso, sino por que el muro deje de mostrarlos todos."""
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM subgrupo")
        return cur.fetchone()[0]


class MuroSubgruposTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.anon = Client(HTTP_HOST=HOST)
        cls.auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.auth.force_login(cls.user)
        from apps.presupuesto.services.muro_subgrupos import muro_subgrupos
        cls.muro = muro_subgrupos()

    def _tarjeta(self, nombre):
        return next((t for t in self.muro["tarjetas"] if t["nombre"] == nombre), None)

    # ── Endpoint ───────────────────────────────────────────────────

    def test_responde_200_autenticado(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        r = self.auth.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["tarjetas"]), _subgrupos_en_bd())

    def test_sin_auth_no_pasa(self):
        r = self.anon.get(URL)
        self.assertIn(r.status_code, (301, 302, 401, 403))

    def test_la_ruta_esta_registrada(self):
        self.assertEqual(reverse("presupuesto:api_muro_subgrupos"), URL)

    # ── Los 45 salen SIEMPRE ───────────────────────────────────────

    def test_salen_todos_los_subgrupos_no_solo_los_que_tienen_datos(self):
        """El LEFT JOIN es el punto del muro: si se vuelve INNER, los subgrupos
        sin proyecto desaparecen y el tablero premia al que no carga.

        Se afirma contra la TABLA, no contra un número escrito acá: el muro
        tiene que mostrar tantas tarjetas como subgrupos haya, sean 45, 46 o
        los que sean mañana. Y la mayoría no tiene nada — si algún día
        `sin_nada` cae a cero, o el área terminó de cargar (buenísimo) o el
        JOIN se cerró (el defecto que este test vigila); la diferencia se ve en
        que los otros grupos hayan crecido, no en el conteo suelto."""
        self.assertEqual(len(self.muro["tarjetas"]), _subgrupos_en_bd())
        sin_nada = [t for t in self.muro["tarjetas"] if t["grupo"] == "sin_nada"]
        con_algo = [t for t in self.muro["tarjetas"] if t["grupo"] != "sin_nada"]
        self.assertEqual(len(sin_nada) + len(con_algo), _subgrupos_en_bd())
        self.assertGreater(len(sin_nada), 0,
                           "ningún subgrupo vacío: el LEFT JOIN se volvió INNER")

    def test_ninguna_tarjeta_sale_sin_pendientes(self):
        """El gris tiene que decir QUÉ falta; una lista vacía no explica nada."""
        for t in self.muro["tarjetas"]:
            self.assertTrue(t["pendientes"], f"{t['nombre']} salió sin pendientes")

    # ── Que el ledger cuadre ───────────────────────────────────────

    def test_comprometido_y_girado_cuadran_con_lo_medido(self):
        self.assertAlmostEqual(self.muro["ledger"]["comprometido"], COMPROMETIDO, places=2)
        self.assertAlmostEqual(self.muro["ledger"]["girado"], GIRADO, places=2)

    def test_las_45_tarjetas_mas_los_huerfanos_dan_el_ledger(self):
        """Si esto falla, hay plata que se perdió o que se contó dos veces."""
        suma_c = sum(t["comprometido"] for t in self.muro["tarjetas"])
        suma_g = sum(t["girado"] for t in self.muro["tarjetas"])
        self.assertAlmostEqual(suma_c, ATRIBUIDO_COMP, places=2)
        self.assertAlmostEqual(suma_g, ATRIBUIDO_GIR, places=2)
        sin = self.muro["sin_subgrupo"]
        self.assertAlmostEqual(suma_c + sin["comprometido"],
                               self.muro["ledger"]["comprometido"], places=2)
        self.assertAlmostEqual(suma_g + sin["girado"],
                               self.muro["ledger"]["girado"], places=2)

    def test_saldo_es_comprometido_menos_girado(self):
        led = self.muro["ledger"]
        self.assertAlmostEqual(led["saldo"], led["comprometido"] - led["girado"], places=2)

    def test_los_huerfanos_no_desaparecen(self):
        sin = self.muro["sin_subgrupo"]
        self.assertEqual(sin["n_contratos"], HUERFANOS_N)
        self.assertAlmostEqual(sin["comprometido"], HUERFANOS_COMP, places=2)
        self.assertAlmostEqual(sin["girado"], HUERFANOS_GIR, places=2)

    def test_el_saldo_de_los_huerfanos_es_null_a_proposito(self):
        """El girado sale íntegro de un contrato cuyo valor en innovaK es NULL:
        el comprometido no lo contiene y la resta daría un saldo falso."""
        self.assertIsNone(self.muro["sin_subgrupo"]["saldo"])
        self.assertTrue(self.muro["sin_subgrupo"]["saldo_motivo"])

    # ── La trampa del programado replicado ─────────────────────────

    def test_programado_no_se_infla_por_las_filas_replicadas(self):
        """`total_programado` se repite en las 4 vigencias y en cada meta del
        proyecto (280 filas / 28 proyectos). Sin DISTINCT por código el número
        se infla ×10 y el muro publicaría ~$6,6 billones."""
        prog = self.muro["ledger"]["programado"]
        self.assertAlmostEqual(prog["valor"], PROGRAMADO, places=2)
        self.assertEqual(prog["cobertura"]["proyectos_oficiales"], 28)
        self.assertLess(prog["valor"], PROGRAMADO * 2)

    def test_el_factor_de_unidad_va_declarado_en_la_respuesta(self):
        """El origen viene en millones. Si el factor no se publica, nadie puede
        auditar la cifra sin abrir el código."""
        prog = self.muro["ledger"]["programado"]
        self.assertEqual(prog["unidad_origen"], "millones_cop")
        self.assertEqual(prog["factor_aplicado"], 1_000_000)

    def test_saldo_cdp_queda_declarado_como_descartado(self):
        self.assertEqual(self.muro["ledger"]["programado"]["descartado"]["fuente"],
                         "secop_contrato.saldo_cdp")

    # ── La trampa del JOIN sin normalizar ──────────────────────────

    def test_cobertura_pdl_cruza_quitando_ceros_a_la_izquierda(self):
        """innovaK guarda '0002377' y SDP guarda '2377'. Sin normalizar,
        Educación daría 0 cargados: un JOIN vacío disfrazado de dato."""
        res = self.muro["cobertura_pdl"]["resumen"]
        self.assertEqual(res["oficiales"], 28)
        self.assertEqual(res["cargados"], 11)
        self.assertEqual(res["faltan"], 17)
        self.assertEqual(res["innovak_sin_par_oficial"], 1)
        self.assertEqual(res["oficiales"], res["cargados"] + res["faltan"])

    def test_sectores_sin_mapeo_1a1_no_se_atribuyen_a_la_fuerza(self):
        """'Gobierno' reparte entre varios subgrupos. Colgarlo de uno sería
        inventar una atribución; se declara `sin_mapeo` y se ve aparte."""
        por_sector = {s["sector"]: s for s in self.muro["cobertura_pdl"]["por_sector"]}
        self.assertEqual(por_sector["Gobierno"]["mapeo"], "sin_mapeo")
        self.assertIsNone(por_sector["Gobierno"]["subgrupo_id"])
        self.assertEqual(por_sector["Cultura, recreación y deporte"]["mapeo"], "ambiguo")

    # ── La trampa del fan-out en el avance ─────────────────────────

    def test_el_avance_no_infla_el_denominador_con_las_filas_de_avance(self):
        """Con un LEFT JOIN directo a `presu_avance_ind_periodo`, la
        `meta_magnitud` de un indicador se suma tantas veces como filas de
        avance tenga. Medido: Infraestructura daría 19/56 = 33.9% cuando lo
        cierto es 19/43 = 44.2%, y Cultura 0.6% en vez de 0.7%."""
        infra = self._tarjeta("Infraestructura")
        if infra is None:
            self.skipTest("No está el subgrupo Infraestructura")
        self.assertEqual(infra["avance_detalle"]["meta_magnitud"], 43.0)
        self.assertEqual(infra["avance_detalle"]["avance_magnitud"], 19.0)
        self.assertEqual(infra["avance"], 44.2)

    def test_los_23_indicadores_quedan_atribuidos_sin_perder_ninguno(self):
        total = sum(t["avance_detalle"]["indicadores"] for t in self.muro["tarjetas"])
        con_av = sum(t["avance_detalle"]["con_avance"] for t in self.muro["tarjetas"])
        self.assertEqual(total, 23)
        self.assertEqual(con_av, 6)

    def test_avance_es_null_y_nunca_cero_cuando_nadie_reporto(self):
        """Poner 0.0% ahí diría 'no avanzó' cuando lo cierto es 'no se midió'."""
        for nombre in ("Deporte", "Seguridad", "Subsidio tipo C"):
            t = self._tarjeta(nombre)
            if t is None:
                continue
            self.assertEqual(t["avance_detalle"]["con_avance"], 0)
            self.assertIsNone(t["avance"], f"{nombre} salió con avance {t['avance']}")

    def test_las_24_metas_quedan_atribuidas(self):
        self.assertEqual(sum(t["n_metas"] for t in self.muro["tarjetas"]), 24)

    # ── El semáforo ────────────────────────────────────────────────

    def test_el_silencio_no_se_castiga_ni_se_premia(self):
        """Un subgrupo sin contratos no puede salir verde (premiaría el
        silencio) ni rojo (lo acusaría de incumplir cuando nadie cargó)."""
        for t in self.muro["tarjetas"]:
            if t["n_contratos"] == 0 or t["cobertura"]["contratos_con_valor"] == 0:
                self.assertEqual(t["semaforo"], "incompleto",
                                 f"{t['nombre']} salió {t['semaforo']} sin datos")
                self.assertIsNone(t["pct_girado"])

    def test_el_reparto_del_semaforo_es_el_medido(self):
        """Los CALIFICADOS son los medidos; el resto queda «incompleto».

        Los tres primeros números sí van escritos: son los subgrupos con plata
        de verdad y cambiarlos significa que se movió una atribución. El cuarto
        no, porque es «todos los demás» — subía en uno cada vez que alguien
        creaba un área, y ese rojo no denunciaba nada.
        """
        from collections import Counter
        c = Counter(t["semaforo"] for t in self.muro["tarjetas"])
        self.assertEqual(c["al_dia"], 1)
        self.assertEqual(c["atrasado"], 1)
        self.assertEqual(c["critico"], 2)  # Educación + Seguridad: SECOP reporta $0 girado en ambos
        # Seguridad salió de «incompleto» al recuperar sus 4 contratos.
        calificados = c["al_dia"] + c["atrasado"] + c["critico"]
        self.assertEqual(c["incompleto"], len(self.muro["tarjetas"]) - calificados)
        # Y ni uno solo se queda sin clasificar: la suma tiene que cerrar.
        self.assertEqual(sum(c.values()), len(self.muro["tarjetas"]))

    def test_todo_semaforo_trae_su_motivo(self):
        for t in self.muro["tarjetas"]:
            self.assertTrue(t["semaforo_motivo"], f"{t['nombre']} sin motivo")

    def test_los_umbrales_se_aplican_sobre_el_tiempo_transcurrido(self):
        """Regla dura: verde ≥ tiempo, ámbar ≥ mitad, rojo por debajo."""
        from apps.presupuesto.services.muro_subgrupos import _semaforo
        self.assertEqual(_semaforo(1, 100.0, 41.0, 41.0, conciliados=1)[0], "al_dia")
        self.assertEqual(_semaforo(1, 100.0, 100.0, 41.0, conciliados=1)[0], "al_dia")
        self.assertEqual(_semaforo(1, 100.0, 30.0, 41.0, conciliados=1)[0], "atrasado")
        self.assertEqual(_semaforo(1, 100.0, 20.0, 41.0, conciliados=1)[0], "critico")
        # La tercera guarda: con contratos y con valor, pero sin NINGUNO que
        # cruce con SECOP, el girado 0 es ausencia de fuente y no un hecho.
        self.assertEqual(_semaforo(1, 100.0, 0.0, 41.0, conciliados=0)[0], "incompleto")
        # Sin con qué calcular → incompleto SIEMPRE, nunca crítico.
        self.assertEqual(_semaforo(0, 0.0, 0.0, 41.0)[0], "incompleto")
        self.assertEqual(_semaforo(3, 0.0, 0.0, 41.0)[0], "incompleto")

    def test_la_ventana_del_pdl_no_se_pasa_de_cien(self):
        """El PDL corre 2025→2028: no existe 'meta vencida', pero el % de
        tiempo tampoco puede desbordarse si la fecha se va del cuatrienio."""
        from apps.presupuesto.services.muro_subgrupos import _ventana_pdl
        self.assertEqual(_ventana_pdl(_dt.date(2024, 1, 1))["pct_tiempo_transcurrido"], 0.0)
        self.assertEqual(_ventana_pdl(_dt.date(2030, 1, 1))["pct_tiempo_transcurrido"], 100.0)
        self.assertEqual(_ventana_pdl(_dt.date(2026, 8, 23))["dias_transcurridos"], 599)

    # ── Cabecera: dos cortes y tres causas distintas ───────────────

    def test_la_cabecera_publica_los_dos_cortes(self):
        """SECOP y SDP van con un mes de diferencia. Publicar uno solo haría
        que el ledger mintiera sobre 'programado'."""
        cab = self.muro["cabecera"]
        self.assertIsNotNone(cab["corte"])
        self.assertIsNotNone(cab["corte_pdl_oficial"])
        self.assertNotEqual(cab["corte"], cab["corte_pdl_oficial"])

    def test_cada_chip_declara_su_causa_porque_se_arreglan_distinto(self):
        """Los tres se ven iguales (0 de 25) y son problemas distintos. La UI
        tiene que decir cosas distintas o le pedirá a alguien que escriba
        donde no hay dónde.

        `etapa` cambió de causa el 2026-08-23: con el DDL 010 aplicado ya hay
        columna (`contrato.etapa_codigo` + catálogo `etapa_contrato`), así que
        dejó de ser «no hay dónde guardarlo» y pasó a ser «nadie lo ha
        registrado» — que se arregla capturando, no con más DDL. El chip lo
        deduce solo consultando el catálogo de columnas, por eso el servicio no
        necesitó cambiar: era este test el que tenía quemada la causa vieja.
        """
        chips = self.muro["cabecera"]["chips"]
        self.assertEqual(chips["etapa"]["causa"], "dato_faltante")
        self.assertEqual(chips["forma_pago"]["causa"], "tabla_vacia")
        self.assertEqual(chips["vinculo_proyecto"]["causa"], "dato_faltante")
        for chip in chips.values():
            self.assertEqual(chip["de"], N_CONTRATOS)
            self.assertTrue(chip["detalle"] and chip["accion"])

    def test_el_vinculo_a_proyecto_coincide_con_los_huerfanos(self):
        """Los 5 que no tienen vínculo son exactamente la tarjeta SIN SUBGRUPO."""
        chip = self.muro["cabecera"]["chips"]["vinculo_proyecto"]
        self.assertEqual(chip["con"], VINCULADOS)
        self.assertEqual(chip["de"] - chip["con"],
                         self.muro["sin_subgrupo"]["n_contratos"])

    # ── Forma congelada para el frontend ───────────────────────────

    def test_las_etapas_nacen_declaradas_en_cero_no_omitidas(self):
        """La forma se congela ahora para que el frontend no cambie cuando
        llegue el DDL. Hoy `sin_dato` es exactamente `n_contratos`."""
        for t in self.muro["tarjetas"]:
            self.assertEqual(set(t["etapas"]),
                             {"planeacion", "contratacion", "ejecucion",
                              "liquidacion", "sin_dato"})
            self.assertEqual(t["etapas"]["sin_dato"], t["n_contratos"])

    def test_la_naturaleza_separa_inversion_de_apoyo(self):
        """Sin esto, Almacén sale gris igual que Ambiente y no es lo mismo:
        Almacén no ejecuta inversión local, su gris es correcto y definitivo."""
        inversion = [t for t in self.muro["tarjetas"] if t["naturaleza"] == "inversion"]
        self.assertEqual(len(inversion), 16)

    def test_el_area_planig_solo_marca_las_diez_confirmadas(self):
        con_area = [t for t in self.muro["tarjetas"] if t["area"]]
        self.assertEqual(len(con_area), 10)
        infra = self._tarjeta("Infraestructura")
        if infra is not None:
            self.assertEqual(infra["area"], "Movilidad")

    def test_el_programado_declara_por_donde_se_atribuyo(self):
        """No es lo mismo 'atribuido por proyecto' que 'atribuido por sector'."""
        for t in self.muro["tarjetas"]:
            if t["programado_oficial"] is None:
                self.assertIsNone(t["programado_origen"])
            else:
                self.assertIn(t["programado_origen"], ("proyecto", "sector"))
        ambiente = self._tarjeta("Ambiente")
        if ambiente is not None:
            self.assertEqual(ambiente["programado_origen"], "sector")
            self.assertEqual(ambiente["n_proyectos"], 0)
            self.assertAlmostEqual(ambiente["programado_oficial"], 17_760_050_000.0, places=2)

    def test_la_base_de_atribucion_va_declarada(self):
        """20 de 25 por `contrato_proyecto`; la otra vía daría 5. Si no se
        declara, nadie puede saber cuál se usó."""
        base = self.muro["ledger"]["base_atribucion"]
        self.assertIn("contrato_proyecto", base)
        self.assertIn("contrato_actividad_plan", base)
