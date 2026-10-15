"""La matriz de carriles: cada rol intenta las 22 transiciones.

Es la prueba que el plan pedía en el punto 3.2, y existe por un hueco concreto:
hasta el 2026-10-15 `cambiar_estado` recibía `usuario` y NO comprobaba quién
era, así que cualquiera que alcanzara el endpoint podía aprobar su propia
formulación. Eso es un hallazgo de control interno, no una comodidad.

Estos tests no crean usuarios reales ni tocan formulaciones: prueban la guarda
—`tiene_carril`— y el reparto sembrado en la base. Nunca datos reales: el
repositorio es público.
"""
import unittest
from unittest import mock

from django.db import connection

from apps.login.services import permisos as P


class _Falso:
    """Un usuario de mentira. Lo único que la guarda le pregunta son sus grupos."""

    def __init__(self, grupos=(), superuser=False):
        self.grupos = list(grupos)
        self.is_superuser = superuser
        self.is_authenticated = True
        self.id = 0


def _con(grupos=(), superuser=False):
    u = _Falso(grupos, superuser)
    return u, mock.patch.object(P, "_grupos_usuario", lambda _u: u.grupos)


class RepartoSembradoTests(unittest.TestCase):
    """Lo que está en la base, no lo que creemos que está."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("""SELECT column_name FROM information_schema.columns
                         WHERE table_name = 'formulacion_transicion'
                           AND column_name = 'rol_requerido'""")
            if not c.fetchone():
                raise unittest.SkipTest("DDL 037 sin aplicar")
            c.execute("""SELECT origen, destino, rol_requerido
                         FROM formulacion_transicion ORDER BY origen, destino""")
            cls.filas = c.fetchall()

    def test_ninguna_transicion_queda_sin_carril(self):
        """Una transición sin carril es inalcanzable salvo para un superusuario.

        Si eso pasa por olvido en vez de por decisión, el flujo se tranca y
        nadie sabe por qué.
        """
        huerfanas = [(o, d) for o, d, r in self.filas if not r]
        self.assertEqual(huerfanas, [],
                         f"transiciones sin rol_requerido: {huerfanas}")

    def test_los_carriles_son_los_tres_que_dijo_la_alcaldia(self):
        """Tres, no los cinco de los documentos entregados."""
        carriles = {r for _, _, r in self.filas}
        self.assertEqual(carriles, {"formulador", "contratacion", "presupuesto"})

    def test_el_formulador_no_puede_aprobar_su_propia_formulacion(self):
        """El hueco que cerró 1.7, dicho como invariante.

        «En revisión → Aprobada» no puede ser del formulador bajo ninguna
        circunstancia: es la definición de que alguien revise.
        """
        aprobar = [r for o, d, r in self.filas if (o, d) == (5, 8)]
        self.assertEqual(aprobar, ["contratacion"],
                         "la aprobación quedó en manos de quien formula")

    def test_el_acto_final_es_de_presupuesto(self):
        final = [r for o, d, r in self.filas if (o, d) == (8, 9)]
        self.assertEqual(final, ["presupuesto"])

    def test_cancelar_no_es_de_un_solo_carril(self):
        """Dárselo a uno permitiría cancelar el trabajo de otro.

        Cancelar desde «Borrador» es del formulador; desde «En revisión», de
        contratación.
        """
        cancelar = {r for o, d, r in self.filas if d == 10}
        self.assertGreater(len(cancelar), 1,
                           "todas las cancelaciones quedaron en un solo carril")


class GuardaTests(unittest.TestCase):
    """`tiene_carril`: niega por defecto, y el prefijo del coordinador."""

    def test_niega_a_quien_no_tiene_grupo(self):
        u, parche = _con([])
        with parche:
            for carril in ("formulador", "contratacion", "presupuesto"):
                self.assertFalse(P.tiene_carril(u, carril))

    def test_cualquier_grupo_coordinador_formula(self):
        """El subgrupo sale de CUÁL coordinador sea, pero el carril es la familia.

        Así lo dijo la Alcaldía: el líder del subgrupo formula, y en la base eso
        es `Coordinador*`.
        """
        for grupo in ("Coordinador", "CoordinadorDeportes", "CoordinadorCultura"):
            u, parche = _con([grupo])
            with parche:
                self.assertTrue(P.tiene_carril(u, "formulador"),
                                f"{grupo} no entró al carril del formulador")
                self.assertFalse(P.tiene_carril(u, "contratacion"))
                self.assertFalse(P.tiene_carril(u, "presupuesto"))

    def test_contratacion_es_lider_contrato_y_no_por_prefijo(self):
        """Los carriles no-formulador se comparan por nombre EXACTO.

        Si se compararan por prefijo, un grupo nuevo llamado
        `Lider_contrato_visor` heredaría la facultad de aprobar.
        """
        u, parche = _con(["Lider_contrato"])
        with parche:
            self.assertTrue(P.tiene_carril(u, "contratacion"))
        u2, parche2 = _con(["Lider_contrato_visor"])
        with parche2:
            self.assertFalse(P.tiene_carril(u2, "contratacion"),
                             "el carril de contratación se está comparando por "
                             "prefijo: un grupo de solo lectura podría aprobar")

    def test_un_carril_sin_grupo_no_lo_tiene_nadie(self):
        """La puesta en marcha segura.

        Mientras el grupo de un carril no exista, su transición no la puede
        hacer nadie salvo un superusuario. Que el flujo se tranque se ve; que
        cualquiera apruebe, no.
        """
        u, parche = _con(["Admin", "Lider", "Gestor", "Visor"])
        with parche:
            self.assertFalse(P.tiene_carril(u, "presupuesto"))

    def test_el_superusuario_pasa_por_todos(self):
        u, parche = _con([], superuser=True)
        with parche:
            for carril in ("formulador", "contratacion", "presupuesto"):
                self.assertTrue(P.tiene_carril(u, carril))

    def test_un_carril_inventado_se_niega(self):
        """Un nombre mal escrito en la base no puede abrir la puerta."""
        u, parche = _con(["Admin"], superuser=False)
        with parche:
            self.assertFalse(P.tiene_carril(u, "contrataciones"))
            self.assertFalse(P.tiene_carril(u, ""))

    def test_el_grupo_de_presupuesto_no_empieza_por_coordinador(self):
        """La trampa del prefijo, fijada donde se define el carril.

        Un grupo `CoordinadorPresupuesto` entraría en `es_coordinador` y
        heredaría poder de creación en áreas sin que nadie lo decida.
        """
        exactos, _ = P.CARRILES_FORMULACION["presupuesto"]
        for nombre in exactos:
            self.assertFalse(nombre.startswith(P.PREFIJO_COORDINADOR), nombre)
