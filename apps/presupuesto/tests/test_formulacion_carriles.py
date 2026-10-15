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


def _algun_usuario():
    """Cualquier usuario activo, solo para atribuir la autoría en las pruebas.

    No se crea ninguno: el repositorio es público y crear usuarios de prueba en
    la base compartida deja basura con nombre de persona.
    """
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(is_active=True).first()


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

    def test_el_formulador_no_puede_validar_lo_que_formula(self):
        """El hueco que cerró 1.7, dicho como invariante y SIN números fijos.

        Las transiciones no se identifican por su código: el catálogo pasó de
        10 a 17 estados y los códigos se movieron —el 8 era «Aprobada» y ahora
        es «Validado jurídicamente»—. Se identifican por lo que SON: toda
        transición que SALE de un estado de revisión es del revisor, nunca del
        formulador. Es la definición de que alguien revise.
        """
        with connection.cursor() as c:
            c.execute("""SELECT eo.nombre, ed.nombre, t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         JOIN formulacion_estado ed ON ed.orden = t.destino
                         WHERE eo.es_revision AND NOT ed.es_final""")
            desde_revision = c.fetchall()
        self.assertTrue(desde_revision, "ningún estado de revisión tiene salida")
        for origen, destino, carril in desde_revision:
            with self.subTest(de=origen, a=destino):
                self.assertNotEqual(
                    carril, "formulador",
                    f"«{origen}» → «{destino}» la haría el formulador: "
                    f"estaría validando lo que él mismo formuló")

    def test_el_acto_final_es_de_presupuesto(self):
        """Se busca por lo que es —la entrada a la frontera de contratación—,
        no por su código, que se movió al pasar a 17 estados."""
        with connection.cursor() as c:
            c.execute("""SELECT t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         JOIN formulacion_estado ed ON ed.orden = t.destino
                         WHERE eo.bloquea_contratacion
                           AND NOT ed.bloquea_contratacion""")
            entradas = [r[0] for r in c.fetchall()]
        self.assertTrue(entradas, "no hay forma de entrar a contratación")
        self.assertEqual(set(entradas), {"contratacion"},
                         "la entrada a la frontera de contratación cambió de "
                         "carril")

    def test_cancelar_no_es_de_un_solo_carril(self):
        """Dárselo a uno permitiría cancelar el trabajo de otro.

        El destino se busca por `es_final`, no por el número 10: al pasar a 17
        estados «Cancelada» es el 17 y el 10 es «En comité».
        """
        with connection.cursor() as c:
            c.execute("""SELECT orden FROM formulacion_estado
                         WHERE es_final AND nombre = 'Cancelada'""")
            fila = c.fetchone()
        self.assertIsNotNone(fila, "no hay estado Cancelada")
        cancelar = {r for o, d, r in self.filas if d == fila[0]}
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


class EvidenciaYBajaTests(unittest.TestCase):
    """Dos defectos que encontró el recorrido de punta a punta (3.1 y 3.3).

    Los dos son la misma preocupación: que la evidencia de un expediente
    contractual no se pueda afirmar sin prueba ni destruir sin vuelta.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("""SELECT COUNT(*) FROM information_schema.columns
                         WHERE table_name = 'formulacion_documento'
                           AND column_name = 'eliminado_en'""")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("DDL 038 sin aplicar")

    def test_el_borrado_de_un_soporte_es_reversible(self):
        """3.3 · Antes, un DELETE destruía la fila Y el blob, sin vuelta.

        Y el blob se borraba FUERA de la transacción, así que ni un fallo
        posterior lo devolvía. Un soporte de expediente contractual no puede
        desaparecer con una petición.

        Se prueba el COMPORTAMIENTO, no el texto del código. La primera versión
        de este test buscaba la cadena «d.delete()» en el fuente y fallaba por
        encontrarla en el COMENTARIO que explica que antes estaba ahí: buscar un
        nombre no comprueba una propiedad.

        Todo ocurre dentro de un rollback y sin tocar Mongo: la fila se crea con
        `mongo_id` nulo, que es lo que permite probar la baja sin un blob.
        """
        from django.db import transaction
        from django.utils import timezone

        from apps.presupuesto.models import DocumentoFormulacion, Formulacion

        f = Formulacion.objects.order_by("id").first()
        if f is None:
            self.skipTest("no hay formulaciones")
        usuario = _algun_usuario()
        if usuario is None:
            self.skipTest("no hay usuario para atribuir la baja")

        class Deshacer(Exception):
            pass

        resultado = {}
        try:
            with transaction.atomic():
                d = DocumentoFormulacion.objects.create(
                    formulacion=f, tipo="prueba", mongo_id=None,
                    nombre_archivo="_PRUEBA_baja_logica.pdf",
                    mime="application/pdf", tamano_bytes=1,
                    subido_por_id=usuario.id, created_at=timezone.now())
                # Lo que hace hoy el endpoint: marcar, no destruir.
                d.eliminado_en = timezone.now()
                d.eliminado_por_id = usuario.id
                d.eliminado_motivo = "prueba de baja lógica"
                d.save(update_fields=["eliminado_en", "eliminado_por",
                                      "eliminado_motivo"])
                resultado["sigue"] = DocumentoFormulacion.objects.filter(
                    id=d.id).exists()
                resultado["marcado"] = DocumentoFormulacion.objects.filter(
                    id=d.id, eliminado_en__isnull=False).exists()
                # Y deja de contar como soporte vivo de la formulación.
                from apps.presupuesto.api.formulacion_views import _documentos_de
                resultado["en_listado"] = any(
                    x.get("id") == d.id for x in _documentos_de(f))
                raise Deshacer()
        except Deshacer:
            pass

        self.assertTrue(resultado["sigue"],
                        "la fila del soporte se destruyó: la baja no es reversible")
        self.assertTrue(resultado["marcado"], "la baja no quedó marcada")
        self.assertFalse(resultado["en_listado"],
                         "un soporte dado de baja sigue apareciendo en el listado")

    def test_la_baja_exige_decir_quien(self):
        """Una baja sin autor es indistinguible de una fila corrupta.

        Lo sostiene un CHECK, y se prueba rompiéndolo: un CHECK que nunca se
        intentó violar no se sabe si está puesto.
        """
        from django.db import transaction
        from django.db.utils import IntegrityError
        from django.utils import timezone

        from apps.presupuesto.models import DocumentoFormulacion, Formulacion

        f = Formulacion.objects.order_by("id").first()
        usuario = _algun_usuario()
        if f is None or usuario is None:
            self.skipTest("sin formulación o sin usuario")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                d = DocumentoFormulacion.objects.create(
                    formulacion=f, tipo="prueba", mongo_id=None,
                    nombre_archivo="_PRUEBA_sin_autor.pdf",
                    mime="application/pdf", tamano_bytes=1,
                    subido_por_id=usuario.id, created_at=timezone.now())
                with connection.cursor() as c:
                    c.execute("""UPDATE formulacion_documento
                                    SET eliminado_en = now(),
                                        eliminado_por_id = NULL
                                  WHERE id = %s""", [d.id])

    def test_el_listado_no_muestra_los_dados_de_baja(self):
        """Sin el filtro, una baja lógica no se comporta como una baja."""
        import inspect

        from apps.presupuesto.api import formulacion_views as V
        src = inspect.getsource(V._documentos_de)
        self.assertIn("eliminado_en__isnull=True", src,
                      "el listado dejó de filtrar los dados de baja: "
                      "seguirían apareciendo y contando como evidencia")

    def test_un_requisito_con_evidencia_no_se_marca_sin_ella(self):
        """3.1 · Los 8 requisitos que piden soporte se marcaban «ok» sin ninguno.

        Y la completitud los contaba, así que una formulación llegaba al 100 % y
        a «Lista para contratación» sin una sola prueba adjunta. El sistema ya
        tenía la intención escrita del otro lado —al borrar el soporte el
        requisito vuelve a pendiente— y faltaba impedir la afirmación.
        """
        import inspect

        from apps.presupuesto.api import formulacion_views as V
        src = inspect.getsource(V.FormulacionRequisitoView.post)
        self.assertIn("exige_evidencia", src,
                      "el endpoint dejó de comprobar la evidencia")
        self.assertIn("documento__isnull=False", src)

    def test_la_mitad_de_las_casillas_exige_soporte(self):
        """El techo sin documentos es 50 %, no 100 %. Es la cifra que cambia.

        Si mañana alguien quita la exigencia, esta prueba lo dice: el número de
        requisitos que piden evidencia es una decisión del catálogo, no un
        detalle.
        """
        with connection.cursor() as c:
            c.execute("""SELECT COUNT(*) FILTER (WHERE exige_evidencia),
                                COUNT(*),
                                COUNT(*) FILTER (WHERE bloquea AND exige_evidencia)
                         FROM formulacion_requisito WHERE activo""")
            con_ev, total, bloquean = c.fetchone()
        self.assertEqual((con_ev, total), (8, 16))
        self.assertGreaterEqual(
            bloquean, 1,
            "ningún requisito que bloquea contratación pide evidencia: "
            "entonces se puede llegar a contratación sin una sola prueba")


class MatrizDePermisosTests(unittest.TestCase):
    """3.2 · Cada actor intenta las 22 transiciones. Las 22, no una muestra.

    El plan la pedía como «la prueba que» cierra el flujo, y la razón es que un
    reparto de permisos se rompe por el caso que nadie miró: basta que una
    transición quede abierta para que alguien apruebe lo que no debe.

    La matriz se construye desde la BASE —`formulacion_transicion
    .rol_requerido`— y no desde una lista escrita acá. Si alguien cambia el
    reparto con un UPDATE, esta prueba cambia con él y sigue siendo cierta; una
    lista copiada en el test se habría quedado vieja en silencio.

    Son 5 actores × 22 transiciones = 110 comprobaciones.
    """

    ACTORES = {
        "formulador":   ["CoordinadorDeportes"],
        "contratacion": ["Lider_contrato"],
        "presupuesto":  ["Presupuesto"],
        "ninguno":      ["Visor", "UsuarioGeneral"],
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("""SELECT column_name FROM information_schema.columns
                         WHERE table_name = 'formulacion_transicion'
                           AND column_name = 'rol_requerido'""")
            if not c.fetchone():
                raise unittest.SkipTest("DDL 037 sin aplicar")
            c.execute("""SELECT t.origen, eo.nombre, t.destino, ed.nombre,
                                t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         JOIN formulacion_estado ed ON ed.orden = t.destino
                         ORDER BY t.origen, t.destino""")
            cls.transiciones = c.fetchall()

    def test_la_matriz_completa_sin_una_sola_casilla_abierta(self):
        """Cada actor pasa SOLO en sus transiciones, y en todas las suyas."""
        permitidas = {a: 0 for a in self.ACTORES}
        for carril_actor, grupos in self.ACTORES.items():
            u, parche = _con(grupos)
            with parche:
                for o, no_, d, nd, carril in self.transiciones:
                    esperado = (carril_actor == carril)
                    obtenido = P.tiene_carril(u, carril)
                    with self.subTest(actor=carril_actor, de=no_, a=nd):
                        self.assertEqual(
                            obtenido, esperado,
                            f"«{no_}» → «{nd}» la hace {carril}; el actor "
                            f"{carril_actor} "
                            f"{'pasó y no debía' if obtenido else 'no pasó y debía'}")
                    permitidas[carril_actor] += int(obtenido)
        # El reparto completo, dicho en números: 13/5/4 y cero para nadie.
        self.assertEqual(permitidas["ninguno"], 0,
                         "un actor sin carril pudo ejecutar transiciones")
        self.assertEqual(sum(permitidas.values()), len(self.transiciones),
                         "las transiciones permitidas no suman 22: hay alguna "
                         "casilla abierta a dos carriles o cerrada a todos")

    def test_el_superusuario_pasa_en_las_22(self):
        """Es el fallo seguro de la puesta en marcha, y tiene que ser total.

        Si un superusuario no pudiera, un carril sin usuarios asignados dejaría
        el flujo trancado sin salida.
        """
        u, parche = _con([], superuser=True)
        with parche:
            for o, no_, d, nd, carril in self.transiciones:
                with self.subTest(de=no_, a=nd):
                    self.assertTrue(P.tiene_carril(u, carril))

    def test_ningun_actor_puede_las_22(self):
        """Si uno pudiera todas, el flujo no sería una separación de funciones.

        Es la invariante de control interno: quien formula no aprueba y quien
        aprueba no da el paso final.
        """
        for carril_actor, grupos in self.ACTORES.items():
            u, parche = _con(grupos)
            with parche:
                puede = sum(1 for *_, carril in self.transiciones
                            if P.tiene_carril(u, carril))
            with self.subTest(actor=carril_actor):
                self.assertLess(puede, len(self.transiciones),
                                f"{carril_actor} puede ejecutar las 22")

    def test_los_tres_actos_clave_caen_en_tres_carriles_distintos(self):
        """Someter, resolver la revisión y cruzar a contratación.

        Los tres se identifican por lo que SON y no por su código, que se movió
        al pasar de 10 a 17 estados. Si someter y resolver cayeran en el mismo
        carril, la revisión sería decorativa.
        """
        with connection.cursor() as c:
            c.execute("""SELECT t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         JOIN formulacion_estado ed ON ed.orden = t.destino
                         WHERE NOT eo.es_revision AND ed.es_revision""")
            somete = {r[0] for r in c.fetchall()}
            c.execute("""SELECT t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         WHERE eo.es_revision""")
            resuelve = {r[0] for r in c.fetchall()}
            c.execute("""SELECT t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         JOIN formulacion_estado ed ON ed.orden = t.destino
                         WHERE eo.bloquea_contratacion
                           AND NOT ed.bloquea_contratacion""")
            cruza = {r[0] for r in c.fetchall()}
        # El formulador somete, pero no es el único: «Planeación validada →
        # Revisión de Contratos» la hace contratación, pasándolo a su propia
        # revisión siguiente. Eso es legítimo y la primera versión de este test
        # lo declaraba un error.
        self.assertIn("formulador", somete,
                      f"el formulador no puede someter a revisión: {somete}")
        self.assertNotIn("presupuesto", somete,
                         "presupuesto somete a revisión: su carril está "
                         "pasada la frontera, no antes")
        self.assertNotIn("formulador", resuelve,
                         "el formulador resuelve su propia revisión")
        self.assertEqual(cruza, {"contratacion"})
        # Y presupuesto manda del otro lado de la frontera.
        with connection.cursor() as c:
            c.execute("""SELECT DISTINCT t.rol_requerido
                         FROM formulacion_transicion t
                         JOIN formulacion_estado eo ON eo.orden = t.origen
                         WHERE NOT eo.bloquea_contratacion AND NOT eo.es_final""")
            despues = {r[0] for r in c.fetchall()}
        self.assertEqual(despues, {"presupuesto"},
                         f"pasada la frontera manda otro carril: {despues}")
