"""Tests del dominio FORMULACIÓN.

Se apoya en la BD externa compartida, sin fixtures, igual que el resto de la
suite. **Estos tests ESCRIBEN**, así que cada uno limpia lo suyo en `finally`,
sin excepción: la base es de producción y una prueba que dejó basura ya le
costó una tarde a este proyecto.

Lo que se protege acá son las tres cosas que el repo no tenía y que, si se
rompen, se rompen en silencio:

  · que no se pueda saltar un estado (hoy los otros dominios sí dejan);
  · que `no_aplica` quede FUERA del denominador (la diferencia entre medir y
    castigar);
  · que el silencio no se califique (una formulación que nadie tocó no está
    «bloqueada»: no ha empezado).
"""
import unittest

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.presupuesto.models import (
    EstadoFormulacion, Formulacion, RequisitoCumplido, RequisitoFormulacion,
    TransicionFormulacion,
)
from apps.presupuesto.services.formulacion import (
    TransicionInvalida, cambiar_estado, catalogo_estados, completitud,
    destinos_validos, semaforo,
)

#: La actividad del Banco de Iniciativas de Deporte — el caso que fijó el
#: modelo. Si algún día no existe, los tests se saltan en vez de fallar.
ACTIVIDAD_BANCO = 108
SUBGRUPO_DEPORTE = 2
#: Vigencia lejana a propósito: no colisiona con lo que un área cargue de
#: verdad, y el UNIQUE es por (actividad, vigencia).
VIGENCIA_PRUEBA = 2027


def _hay_dominio():
    return EstadoFormulacion.objects.exists()


class CatalogoDeEstadosTests(unittest.TestCase):
    """El catálogo y el grafo: se leen, no se calculan."""

    def setUp(self):
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")

    def test_solo_un_estado_no_bloquea_la_contratacion(self):
        """`bloquea_contratacion=False` ES la frontera del ciclo. Si un día hay
        dos, alguien abrió una puerta lateral a contratación."""
        abiertos = [e["nombre"] for e in catalogo_estados()
                    if not e["bloquea_contratacion"]]
        self.assertEqual(abiertos, ["Lista para contratación"])

    def test_todo_destino_del_grafo_es_un_estado_que_existe(self):
        codigos = {e["codigo"] for e in catalogo_estados()}
        for t in TransicionFormulacion.objects.all():
            with self.subTest(transicion=f"{t.origen_id}→{t.destino_id}"):
                self.assertIn(t.origen_id, codigos)
                self.assertIn(t.destino_id, codigos)

    def test_no_hay_transiciones_a_si_mismo(self):
        """Un bucle A→A dejaría «cambiar de estado» sin cambiar nada, y encima
        auditado como si algo hubiera pasado."""
        bucles = [t for t in TransicionFormulacion.objects.all()
                  if t.origen_id == t.destino_id]
        self.assertEqual(bucles, [])

    def test_del_estado_final_no_sale_ninguna_transicion(self):
        """De «Cancelada» no se vuelve. Reabrirla sin rastro borraría el motivo
        por el que se canceló."""
        for e in EstadoFormulacion.objects.filter(es_final=True):
            with self.subTest(estado=e.nombre):
                self.assertEqual(destinos_validos(e.codigo), [])

    def test_desde_borrador_no_se_llega_a_contratacion(self):
        """El agujero exacto que tienen hoy los otros dominios del repo."""
        destinos = {d["nombre"] for d in destinos_validos(1)}
        self.assertNotIn("Lista para contratación", destinos)



class FormulacionVivaTests(unittest.TestCase):
    """Los que escriben. Cada uno limpia lo suyo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()

    def setUp(self):
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")
        if not RequisitoFormulacion.objects.filter(activo=True).exists():
            self.skipTest("el catálogo de requisitos está vacío: falta el seed")
        from apps.presupuesto.models import ActividadPlan
        if not ActividadPlan.objects.filter(id=ACTIVIDAD_BANCO).exists():
            self.skipTest("la actividad del Banco ya no está en esta base")
        self.f = Formulacion.objects.create(
            actividad_plan_id=ACTIVIDAD_BANCO, vigencia_id=VIGENCIA_PRUEBA,
            subgrupo_id=SUBGRUPO_DEPORTE,
            objeto="ZZZ_PRUEBA_BORRAR — formulación de test",
            estado_id=1, estado_fecha=timezone.now(), creado_en=timezone.now())

    def tearDown(self):
        """Limpia TODO lo que el test escribió, incluida la auditoría.

        La primera versión sólo borraba la formulación y sus requisitos, y
        dejaba 18 filas en `auditoria_dato` — que `cambiar_estado` escribe por
        diseño. Sobre una base compartida, un test que deja rastro contamina la
        tabla que existe justamente para tener rastro fiable.
        """
        from apps.presupuesto.models.auditoria import AuditoriaDato
        f = getattr(self, "f", None)
        if f is not None:
            AuditoriaDato.objects.filter(entidad="formulacion", entidad_id=f.id).delete()
            RequisitoCumplido.objects.filter(formulacion=f).delete()
            Formulacion.objects.filter(id=f.id).delete()

    def _marcar(self, **por_codigo):
        """Marca requisitos; los no nombrados quedan sin registrar (`sin_dato`)."""
        for codigo, estado in por_codigo.items():
            RequisitoCumplido.objects.update_or_create(
                formulacion=self.f, requisito_id=codigo,
                defaults={"estado": estado, "fecha": timezone.now()})

    # ── completitud ────────────────────────────────────────────────────
    def test_el_silencio_no_se_califica(self):
        """Una formulación que nadie tocó NO está bloqueada: no ha empezado.
        Pintarla de rojo acusaría a un área de incumplir algo que todavía no le
        tocaba — es la regla del muro con los subgrupos sin datos."""
        s = semaforo(self.f)
        self.assertEqual(s["clave"], "sin_iniciar")
        self.assertEqual(completitud(self.f)["revisados"], 0)

    def test_no_aplica_queda_fuera_del_denominador(self):
        antes = completitud(self.f)["aplicables"]
        self._marcar(analisis_sector="no_aplica")
        despues = completitud(self.f)
        self.assertEqual(despues["aplicables"], antes - 1)
        self.assertEqual(despues["no_aplica"], 1)

    def test_puede_ir_alto_y_seguir_bloqueada(self):
        """El §12 del plan, literal: al 90 % y bloqueada por un crítico."""
        todos = {r.codigo: "ok" for r in RequisitoFormulacion.objects.filter(activo=True)}
        todos["cdp"] = "pendiente"
        self._marcar(**todos)
        c = completitud(self.f)
        self.assertGreaterEqual(c["pct"], 90)
        self.assertTrue(c["bloqueada"])
        self.assertIn("CDP", " ".join(c["faltan_criticos"]))
        self.assertEqual(semaforo(self.f, c)["clave"], "bloqueada")

    def test_el_pct_es_null_y_no_cero_si_no_hay_nada_que_medir(self):
        """Un 0 % diría «no hizo nada»; `null` dice «no hay qué medir». No es lo
        mismo y el proyecto ya decidió que no se confunden."""
        self._marcar(**{r.codigo: "no_aplica"
                        for r in RequisitoFormulacion.objects.filter(activo=True)})
        self.assertIsNone(completitud(self.f)["pct"])

    # ── transiciones ───────────────────────────────────────────────────
    def test_no_se_puede_saltar_un_estado(self):
        with self.assertRaises(TransicionInvalida):
            cambiar_estado(self.f, 9, self.user)

    def test_no_se_pasa_a_contratacion_con_un_critico_pendiente(self):
        todos = {r.codigo: "ok" for r in RequisitoFormulacion.objects.filter(activo=True)}
        todos["cdp"] = "pendiente"
        self._marcar(**todos)
        for destino in (2, 3, 5, 8):
            cambiar_estado(self.f, destino, self.user)
        with self.assertRaises(TransicionInvalida) as ctx:
            cambiar_estado(self.f, 9, self.user)
        self.assertIn("CDP", str(ctx.exception))

    def test_el_camino_completo_llega_a_lista(self):
        self._marcar(**{r.codigo: "ok"
                        for r in RequisitoFormulacion.objects.filter(activo=True)})
        for destino in (2, 3, 5, 8, 9):
            cambiar_estado(self.f, destino, self.user)
        self.f.refresh_from_db()
        self.assertFalse(self.f.estado.bloquea_contratacion)
        self.assertEqual(semaforo(self.f)["clave"], "lista")

    def test_el_mensaje_de_error_dice_a_donde_SI_se_puede(self):
        """Un «no se puede» sin alternativa deja al usuario adivinando."""
        with self.assertRaises(TransicionInvalida) as ctx:
            cambiar_estado(self.f, 9, self.user)
        self.assertIn("En elaboración", str(ctx.exception))

    def test_cada_transicion_queda_auditada(self):
        from apps.presupuesto.models.auditoria import AuditoriaDato
        antes = AuditoriaDato.objects.filter(entidad="formulacion",
                                             entidad_id=self.f.id).count()
        cambiar_estado(self.f, 2, self.user)
        filas = AuditoriaDato.objects.filter(entidad="formulacion",
                                             entidad_id=self.f.id)
        self.assertEqual(filas.count(), antes + 1)
        fila = filas.order_by("-id").first()
        self.assertEqual(fila.campo, "estado")
        self.assertEqual(fila.valor_anterior, "Borrador")
        self.assertEqual(fila.valor_nuevo, "En elaboración")
        self.assertIsNotNone(fila.subgrupo_id)   # el `tearDown` la borra

    # ── la base como red ───────────────────────────────────────────────
    def test_una_actividad_se_formula_una_vez_por_vigencia(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Formulacion.objects.create(
                    actividad_plan_id=ACTIVIDAD_BANCO, vigencia_id=VIGENCIA_PRUEBA,
                    subgrupo_id=SUBGRUPO_DEPORTE, objeto="ZZZ_PRUEBA duplicada",
                    estado_id=1, estado_fecha=timezone.now(), creado_en=timezone.now())

    def test_cancelar_exige_motivo_y_autor(self):
        """Los tres van juntos o ninguno, y lo garantiza un CHECK: una
        cancelación sin motivo no se puede defender."""
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Formulacion.objects.filter(id=self.f.id).update(
                    cancelado_en=timezone.now())
