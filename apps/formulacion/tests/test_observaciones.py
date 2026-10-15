"""Las observaciones: el ciclo, quién mueve cada paso y las dos compuertas.

Antes del DDL 039, «Con observaciones» era solo un estado y el texto iba —si
acaso— en el campo de auditoría del cambio de estado. Devolver una formulación
era un gesto: un estado y un párrafo, sin sección, sin requisito y sin forma de
responder una cosa y no otra.

Todo corre DENTRO de transacciones que se deshacen: la base es de producción y
las formulaciones son reales.
"""
import unittest

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.formulacion.services import flujo as F
from apps.formulacion.services import observaciones as OBS


class _Deshacer(Exception):
    pass


def _su():
    return get_user_model().objects.filter(is_superuser=True, is_active=True).first()


def _una_formulacion():
    from apps.formulacion.models import Formulacion
    return Formulacion.objects.select_related("estado", "actividad_plan").order_by("id").first()


class CicloTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('public.formulacion_observacion') IS NOT NULL")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("DDL 039 sin aplicar")
        if _su() is None or _una_formulacion() is None:
            raise unittest.SkipTest("sin superusuario o sin formulaciones")

    def test_el_ciclo_completo_y_quien_mueve_cada_paso(self):
        """abierta → respondida → atendida, y cerrar NO es de quien responde."""
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                r = OBS.crear(f, su, "Falta el soporte del estudio de mercado.",
                              requisito_codigo="estudio_mercado")
                self.assertEqual(r["estado"], OBS.ABIERTA)
                o = OBS.listar(f.id)[-1]
                # La sección se deduce del requisito: así no pueden discrepar.
                self.assertEqual(o["seccion"], "tecnico")
                self.assertEqual(o["autor_carril"], "formulador")  # superusuario

                OBS.responder(f, r["id"], su, "Se adjuntó el estudio corregido.")
                self.assertEqual(OBS.resumen(f.id)["respondidas"], 1)

                OBS.cerrar(f, r["id"], su, OBS.ATENDIDA)
                o = [x for x in OBS.listar(f.id) if x["id"] == r["id"]][0]
                self.assertEqual(o["estado"], OBS.ATENDIDA)
                self.assertFalse(o["pendiente"])
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_no_se_da_por_atendida_una_que_nadie_respondio(self):
        """Cerrar sin respuesta deja el expediente diciendo que se resolvió."""
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                r = OBS.crear(f, su, "El valor estimado no cuadra con el CDP.")
                with self.assertRaises(OBS.ObservacionInvalida):
                    OBS.cerrar(f, r["id"], su, OBS.ATENDIDA)
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_desestimar_exige_motivo(self):
        """Sin motivo, retirar una observación es indistinguible de borrarla."""
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                r = OBS.crear(f, su, "Revisar la matriz de riesgos del anexo.")
                with self.assertRaises(OBS.ObservacionInvalida):
                    OBS.cerrar(f, r["id"], su, OBS.DESESTIMADA)
                OBS.cerrar(f, r["id"], su, OBS.DESESTIMADA,
                           motivo="Se observó por error: el anexo sí la traía.")
                o = [x for x in OBS.listar(f.id) if x["id"] == r["id"]][0]
                self.assertEqual(o["estado"], OBS.DESESTIMADA)
                self.assertTrue(o["cierre_motivo"])
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_una_observacion_de_tres_letras_no_sirve(self):
        """El formulador tiene que poder saber qué corregir."""
        su, f = _su(), _una_formulacion()
        for texto in ("", "   ", "ojo", "falta"):
            with self.subTest(texto=texto):
                with self.assertRaises(OBS.ObservacionInvalida):
                    OBS.crear(f, su, texto)

    def test_no_existe_funcion_de_borrado(self):
        """Las Historias lo piden: «atendidas sin eliminarlas».

        Se comprueba sobre el MÓDULO, no sobre el texto del fuente: lo que
        importa es que no haya una función que borre, no que la palabra no
        aparezca en un comentario.
        """
        publicas = [n for n in dir(OBS) if not n.startswith("_")]
        for nombre in publicas:
            self.assertNotIn(
                nombre.lower(), ("borrar", "eliminar", "delete", "purgar"),
                f"el servicio expone «{nombre}»: una observación no se borra")


class CompuertasTests(unittest.TestCase):
    """Las dos que hacen que «Con observaciones» signifique algo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('public.formulacion_observacion') IS NOT NULL")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("DDL 039 sin aplicar")
        if _su() is None or _una_formulacion() is None:
            raise unittest.SkipTest("sin superusuario o sin formulaciones")

    def _hasta_revision(self, f, su):
        """Lleva la formulación al PRIMER estado de revisión, sin códigos fijos.

        El catálogo pasó de 10 a 17 estados y los códigos se movieron: la
        primera versión de esto decía `(2, 3, 5)` y el 5 dejó de ser «En
        revisión». Se camina siguiendo los destinos válidos hasta encontrar un
        estado marcado `es_revision`.
        """
        from apps.formulacion.models import EstadoFormulacion
        for _ in range(12):
            f.refresh_from_db()
            if f.estado.es_revision:
                return
            siguiente = None
            for d in F.destinos_validos(f.estado.codigo):
                e = EstadoFormulacion.objects.get(codigo=d["codigo"])
                if not e.es_final and e.orden > f.estado.orden:
                    siguiente = e
                    break
            if siguiente is None:
                self.fail(f"no hay camino hacia una revisión desde "
                          f"«{f.estado.nombre}»")
            F.cambiar_estado(f, siguiente.codigo, su)
        self.fail("no se llegó a un estado de revisión en 12 pasos")

    def _observacion_y_vuelta(self, f, su):
        """Devuelve a observación y de ahí al estado de subsanación.

        Devuelve el código del estado de revisión al que hay que reenviar.
        """
        from apps.formulacion.models import EstadoFormulacion
        revision = f.estado.codigo
        obs_destino = next(
            d for d in F.destinos_validos(revision)
            if EstadoFormulacion.objects.get(codigo=d["codigo"]).es_observacion)
        F.cambiar_estado(f, obs_destino["codigo"], su)
        f.refresh_from_db()
        return revision

    def test_no_se_devuelve_con_observaciones_sin_observar_nada(self):
        """Sería una devolución muda: el estado lo afirma y no hay qué corregir."""
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                self._hasta_revision(f, su)
                from apps.formulacion.models import EstadoFormulacion
                obs = next(d for d in F.destinos_validos(f.estado.codigo)
                           if EstadoFormulacion.objects.get(
                               codigo=d["codigo"]).es_observacion)
                with self.assertRaises(F.TransicionInvalida) as ctx:
                    F.cambiar_estado(f, obs["codigo"], su)
                self.assertIn("al menos una observación", str(ctx.exception))
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_no_se_reenvia_a_revision_con_observaciones_sin_responder(self):
        """El revisor volvería a encontrar lo mismo."""
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                self._hasta_revision(f, su)
                OBS.crear(f, su, "Falta la justificación de la necesidad.")
                revision = self._observacion_y_vuelta(f, su)
                with self.assertRaises(F.TransicionInvalida) as ctx:
                    F.cambiar_estado(f, revision, su)
                self.assertIn("sin responder", str(ctx.exception))
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_respondida_basta_para_reenviar_pero_no_cierra(self):
        """Responder desbloquea el reenvío; cerrarla sigue siendo del revisor.

        Es la diferencia entre «ya contesté» y «quedó resuelto», y mezclarlas
        convertiría la observación en un trámite.
        """
        su, f = _su(), _una_formulacion()
        try:
            with transaction.atomic():
                self._hasta_revision(f, su)
                r = OBS.crear(f, su, "Ajustar el cronograma al plazo pactado.")
                revision = self._observacion_y_vuelta(f, su)
                OBS.responder(f, r["id"], su, "Cronograma ajustado a 6 meses.")
                F.cambiar_estado(f, revision, su); f.refresh_from_db()
                self.assertTrue(f.estado.es_revision)
                # y sigue pendiente de cierre
                self.assertEqual(OBS.resumen(f.id)["pendientes"], 1)
                self.assertEqual(OBS.resumen(f.id)["cerradas"], 0)
                raise _Deshacer()
        except _Deshacer:
            pass

    def test_nada_de_esto_quedo_escrito(self):
        """La comprobación que hace honesto probar sobre la base real."""
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM formulacion_observacion")
            self.assertEqual(c.fetchone()[0], 0,
                             "quedaron observaciones de prueba en la base")
            c.execute("SELECT estado_codigo FROM formulacion ORDER BY id LIMIT 1")
            self.assertEqual(c.fetchone()[0], 1,
                             "una formulación real quedó movida de estado")
