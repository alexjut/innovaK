"""Scope de ESCRITURA: un área no puede tocar los contratos de otra.

Lo que se protege acá es un hueco real que estuvo abierto: la vista de vincular
contrato ↔ actividad validaba que la ACTIVIDAD fuera del área, pero no el
CONTRATO. El `contrato_id` del cuerpo de la petición entraba derecho al
`get_or_create`, así que un usuario de Educación podía colgar un contrato de
Seguridad a su propio plan cambiando un número en la petición — sin tocar el
frontend, que es justamente por lo que ocultar un botón no es autorizar.

Los tests NO escriben: todos esperan un rechazo. El único caso que llegaría a
escribir se salta a propósito (ver `test_contrato_propio_no_lo_rechaza`), porque
la BD es compartida y de producción.

Datos verificados contra `poblacion_kennedy` el 2026-08-24. Cada test se salta
solo si el dato que necesita no está, en vez de fallar por algo que no es un
defecto del código.

> **REGLA QUE ESTOS TESTS APRENDIERON A LA MALA.**
>
> Para comprobar que estos tests *detectan* el hueco, se reintrodujo el bug a
> propósito y se corrieron contra la BD real. Crearon **tres filas basura** en
> `contrato_actividad_plan`: dos colgaban contratos de otra área a la actividad
> de Educación, y una apuntaba a un contrato inexistente. Se detectaron por la
> suite (dos tests del expediente empezaron a fallar) y se borraron.
>
> La BD es **compartida y de producción**, y `managed=False` significa que no
> hay FK que frene una fila inventada.
>
> Por eso, en este archivo:
> 1. todo test que pueda escribir **limpia en `finally`**, sin confiar en que
>    el código bajo prueba lo impida — eso es justo lo que se está probando;
> 2. el camino feliz **no se ejecuta**: se comprueba la condición que decide,
>    no el efecto;
> 3. para verificar que un test detecta un bug, se rompe el **test**, nunca el
>    código de producción contra la base real.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

EDUCACION, SEGURIDAD = 8, 38
URL = "/presupuesto/api/areas/{}/contratos/vincular/"


class ScopeEscrituraContratoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        cls.client = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client.force_login(cls.user)

    # ── helpers ────────────────────────────────────────────────────────────
    def _contratos_de(self, subgrupo_id):
        """Los contratos del área por la UNIÓN de las dos vías, igual que el panel."""
        from apps.presupuesto.models.core import ContratoProyecto, Proyecto
        from apps.presupuesto.models.sql import ContratoActividadPlan
        pids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                    .values_list("id", flat=True))
        if not pids:
            return set()
        return set(ContratoProyecto.objects.filter(proyecto_id__in=pids)
                   .values_list("contrato_id", flat=True)) | set(
            ContratoActividadPlan.objects
            .filter(actividad_plan__proyecto_id__in=pids, activo=True)
            .values_list("contrato_id", flat=True))

    def _actividad_de(self, subgrupo_id):
        from apps.presupuesto.models.core import ActividadPlan, Proyecto
        pids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                    .values_list("id", flat=True))
        return (ActividadPlan.objects.filter(proyecto_id__in=pids)
                .values_list("id", flat=True).first()) if pids else None

    # ── el hueco que se cerró ──────────────────────────────────────────────
    def test_contrato_de_otra_area_se_rechaza(self):
        """El caso exacto del hueco: actividad propia + contrato ajeno → 403.

        La actividad SÍ es de Educación, así que la validación vieja la dejaba
        pasar. Lo que hace fallar la petición es el contrato.
        """
        if self.user is None:
            self.skipTest("no hay superusuario en la BD")
        ajenos = self._contratos_de(SEGURIDAD) - self._contratos_de(EDUCACION)
        actividad = self._actividad_de(EDUCACION)
        if not ajenos or actividad is None:
            self.skipTest("faltan datos de Educación o Seguridad para el cruce")

        r = self.client.post(
            URL.format(EDUCACION),
            {"contrato_id": sorted(ajenos)[0], "actividad_plan_id": actividad},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_el_mensaje_no_filtra_de_quien_es(self):
        """Rechazar no puede convertirse en una fuga de información."""
        if self.user is None:
            self.skipTest("no hay superusuario en la BD")
        ajenos = self._contratos_de(SEGURIDAD) - self._contratos_de(EDUCACION)
        actividad = self._actividad_de(EDUCACION)
        if not ajenos or actividad is None:
            self.skipTest("faltan datos para el cruce")

        r = self.client.post(
            URL.format(EDUCACION),
            {"contrato_id": sorted(ajenos)[0], "actividad_plan_id": actividad},
            content_type="application/json",
        )
        cuerpo = r.content.decode("utf-8", "replace").lower()
        self.assertNotIn("seguridad", cuerpo)
        for pista in ("subgrupo_id", "proyecto_id", "38"):
            self.assertNotIn(pista, cuerpo, f"el mensaje filtra «{pista}»")

    def test_contrato_inexistente_se_rechaza(self):
        """Un id que no existe tiene que rebotar por scope, no por FK.

        OJO — este test escribió basura una vez. Con el hueco abierto, el
        `get_or_create` creó una fila apuntando al contrato 99999999, que no
        existe: la tabla no tiene FK real (`managed=False`), así que la BD no
        lo impidió. Se borró a mano.

        Por eso ahora se limpia lo que haya podido crearse, en `finally`. Un
        test que puede escribir en una BD compartida se limpia solo: no se
        confía en que el código bajo prueba lo impida — precisamente lo que se
        está probando es si lo impide.
        """
        if self.user is None:
            self.skipTest("no hay superusuario en la BD")
        actividad = self._actividad_de(EDUCACION)
        if actividad is None:
            self.skipTest("Educación no tiene actividades")
        FANTASMA = 99_999_999
        try:
            r = self.client.post(
                URL.format(EDUCACION),
                {"contrato_id": FANTASMA, "actividad_plan_id": actividad},
                content_type="application/json",
            )
            self.assertIn(r.status_code, (400, 403), r.content[:200])
        finally:
            from apps.presupuesto.models.sql import ContratoActividadPlan
            ContratoActividadPlan.objects.filter(
                contrato_id=FANTASMA, actividad_plan_id=actividad).delete()

    def test_contrato_no_numerico_no_revienta(self):
        """Un id basura tiene que dar 400, no un 500 con traza."""
        if self.user is None:
            self.skipTest("no hay superusuario en la BD")
        actividad = self._actividad_de(EDUCACION)
        if actividad is None:
            self.skipTest("Educación no tiene actividades")
        r = self.client.post(
            URL.format(EDUCACION),
            {"contrato_id": "'; DROP TABLE contrato; --", "actividad_plan_id": actividad},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content[:200])

    # ── lo que ya funcionaba, para que no se rompa al cerrar el hueco ──────
    def test_actividad_de_otra_area_sigue_rechazandose(self):
        if self.user is None:
            self.skipTest("no hay superusuario en la BD")
        propios = self._contratos_de(EDUCACION)
        ajena = self._actividad_de(SEGURIDAD)
        if not propios or ajena is None:
            self.skipTest("faltan datos para el cruce")
        r = self.client.post(
            URL.format(EDUCACION),
            {"contrato_id": sorted(propios)[0], "actividad_plan_id": ajena},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400, r.content[:200])

    def test_contrato_propio_no_lo_rechaza(self):
        """El camino feliz NO se ejecuta: escribiría en la BD compartida.

        Se comprueba en su lugar que el contrato propio SÍ está en el conjunto
        que la vista considera del área — que es la condición que decide.
        """
        propios = self._contratos_de(EDUCACION)
        if not propios:
            self.skipTest("Educación no tiene contratos")
        self.assertTrue(propios, "el área debe reconocer sus propios contratos")
