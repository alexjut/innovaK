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


class EnlaceConContratoTests(unittest.TestCase):
    """El salto formulación → contrato. Lo que se protege es la TRAZA.

    Estos tests escriben y limpian lo suyo: formulación, vínculo y auditoría.
    **Nunca borran un contrato**, ni siquiera uno que el enlace hubiera creado
    — si eso pasara, el test estaría borrando información institucional.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()

    def setUp(self):
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")
        from apps.presupuesto.models import ActividadPlan, SecopContrato
        if not ActividadPlan.objects.filter(id=ACTIVIDAD_BANCO).exists():
            self.skipTest("la actividad del Banco ya no está en esta base")
        if not SecopContrato.objects.exists():
            self.skipTest("el espejo de SECOP está vacío")
        self.f = Formulacion.objects.create(
            actividad_plan_id=ACTIVIDAD_BANCO, vigencia_id=VIGENCIA_PRUEBA,
            subgrupo_id=SUBGRUPO_DEPORTE,
            objeto="ZZZ_PRUEBA_BORRAR — enlace con contrato",
            estado_id=1, estado_fecha=timezone.now(), creado_en=timezone.now())

    def tearDown(self):
        from apps.presupuesto.models import FormulacionContrato
        from apps.presupuesto.models.auditoria import AuditoriaDato
        f = getattr(self, "f", None)
        if f is not None:
            FormulacionContrato.objects.filter(formulacion=f).delete()
            AuditoriaDato.objects.filter(entidad="formulacion", entidad_id=f.id).delete()
            Formulacion.objects.filter(id=f.id).delete()

    # ── la búsqueda ────────────────────────────────────────────────────
    def test_se_busca_por_numero_y_encuentra_el_exacto(self):
        """El caso de respuesta conocida: el CPS-983-2025 existe y ya está en
        innovaK como contrato 97."""
        from apps.presupuesto.services.formulacion_contrato import buscar_en_secop
        r = buscar_en_secop("983", vigencia=2025)
        refs = {x["referencia"] for x in r["resultados"]}
        if "CPS-983-2025" not in refs:
            self.skipTest("el CPS-983-2025 ya no está en el espejo")
        fila = next(x for x in r["resultados"] if x["referencia"] == "CPS-983-2025")
        self.assertTrue(fila["parseable"])
        self.assertIsNotNone(fila["ya_en_innovak"],
                             "el buscador no reconoció que ese contrato ya existe")

    def test_una_busqueda_corta_no_devuelve_medio_secop(self):
        """Dos caracteres empatarían con cientos. Se pide un mínimo y se dice."""
        from apps.presupuesto.services.formulacion_contrato import buscar_en_secop
        r = buscar_en_secop("98")
        self.assertEqual(r["resultados"], [])
        self.assertIsNotNone(r["motivo_vacio"])

    def test_el_vacio_explica_por_que_esta_vacio(self):
        """Un «0 resultados» sin motivo no se puede juzgar: puede ser que no
        exista o que todavía no se haya publicado."""
        from apps.presupuesto.services.formulacion_contrato import buscar_en_secop
        r = buscar_en_secop("ZZZNOEXISTE")
        self.assertEqual(r["resultados"], [])
        self.assertIn("publicado", r["motivo_vacio"])

    # ── el enlace ──────────────────────────────────────────────────────
    def _fila_secop(self):
        from apps.presupuesto.services.formulacion_contrato import buscar_en_secop
        r = buscar_en_secop("983", vigencia=2025)
        for x in r["resultados"]:
            if x["referencia"] == "CPS-983-2025":
                return x
        return None

    def test_enlazar_un_contrato_que_ya_existe_no_crea_otro(self):
        """La regla que impide el duplicado que la precarga vino a eliminar."""
        from apps.presupuesto.models import Contrato
        from apps.presupuesto.services.formulacion_contrato import enlazar_desde_secop
        fila = self._fila_secop()
        if fila is None or not fila["ya_en_innovak"]:
            self.skipTest("no hay un contrato ya presente con el que probar")
        antes = Contrato.objects.count()
        salida = enlazar_desde_secop(self.f, fila["id_contrato"], self.user)
        self.assertFalse(salida["contrato_creado"])
        self.assertEqual(Contrato.objects.count(), antes)
        self.assertEqual(salida["contrato_id"], fila["ya_en_innovak"])

    def test_la_traza_va_en_los_dos_sentidos(self):
        """§15 del plan: desde la formulación y desde el contrato."""
        from apps.presupuesto.services.formulacion_contrato import (
            contratos_de, enlazar_desde_secop, formulaciones_de,
        )
        fila = self._fila_secop()
        if fila is None or not fila["ya_en_innovak"]:
            self.skipTest("no hay un contrato ya presente con el que probar")
        salida = enlazar_desde_secop(self.f, fila["id_contrato"], self.user)
        self.assertIn(salida["contrato_id"],
                      [c["contrato_id"] for c in contratos_de(self.f)])
        self.assertIn(self.f.id,
                      [x["formulacion_id"] for x in formulaciones_de(salida["contrato_id"])])

    def test_no_se_enlaza_dos_veces_el_mismo_contrato(self):
        from apps.presupuesto.services.formulacion_contrato import (
            EnlaceInvalido, enlazar_desde_secop,
        )
        fila = self._fila_secop()
        if fila is None or not fila["ya_en_innovak"]:
            self.skipTest("no hay un contrato ya presente con el que probar")
        enlazar_desde_secop(self.f, fila["id_contrato"], self.user)
        with self.assertRaises(EnlaceInvalido):
            enlazar_desde_secop(self.f, fila["id_contrato"], self.user)

    def test_desenlazar_no_borra_el_contrato(self):
        """Un emparejamiento equivocado se corrige; un contrato borrado no se
        recupera."""
        from apps.presupuesto.models import Contrato
        from apps.presupuesto.services.formulacion_contrato import (
            contratos_de, desenlazar, enlazar_desde_secop,
        )
        fila = self._fila_secop()
        if fila is None or not fila["ya_en_innovak"]:
            self.skipTest("no hay un contrato ya presente con el que probar")
        salida = enlazar_desde_secop(self.f, fila["id_contrato"], self.user)
        desenlazar(self.f, salida["contrato_id"], self.user, motivo="prueba")
        self.assertEqual(contratos_de(self.f), [])
        self.assertTrue(Contrato.objects.filter(id=salida["contrato_id"]).exists())

    def test_una_fila_de_secop_que_no_existe_se_rechaza_con_motivo(self):
        from apps.presupuesto.services.formulacion_contrato import (
            EnlaceInvalido, enlazar_desde_secop,
        )
        with self.assertRaises(EnlaceInvalido) as ctx:
            enlazar_desde_secop(self.f, "ZZZ-NO-EXISTE", self.user)
        self.assertIn("espejo", str(ctx.exception))


class EncargadoTests(unittest.TestCase):
    """El encargado es DATO, no permiso.

    Quién puede tocar una formulación lo siguen decidiendo el scope y el rol.
    Esto dice quién RESPONDE por ella — la pregunta que hay que poder contestar
    para reclamarle a alguien.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()

    def setUp(self):
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")
        from apps.login.models.funcionario import Funcionario
        from apps.presupuesto.models import ActividadPlan
        if not ActividadPlan.objects.filter(id=ACTIVIDAD_BANCO).exists():
            self.skipTest("la actividad del Banco ya no está en esta base")
        self.propios = list(Funcionario.objects.filter(subgrupo_id=SUBGRUPO_DEPORTE)[:1])
        self.ajenos = list(Funcionario.objects.exclude(subgrupo_id=SUBGRUPO_DEPORTE)
                           .filter(subgrupo_id__isnull=False)[:1])
        self.f = Formulacion.objects.create(
            actividad_plan_id=ACTIVIDAD_BANCO, vigencia_id=VIGENCIA_PRUEBA,
            subgrupo_id=SUBGRUPO_DEPORTE, objeto="ZZZ_PRUEBA_BORRAR — encargado",
            estado_id=1, estado_fecha=timezone.now(), creado_en=timezone.now())

    def tearDown(self):
        from apps.presupuesto.models.auditoria import AuditoriaDato
        f = getattr(self, "f", None)
        if f is not None:
            AuditoriaDato.objects.filter(entidad="formulacion", entidad_id=f.id).delete()
            Formulacion.objects.filter(id=f.id).delete()

    def test_nace_sin_encargado_y_lo_dice(self):
        """«Sin encargado» es un pendiente con dueño visible, no un vacío mudo.
        Si se escondiera detrás de un valor por defecto, nunca se llenaría."""
        from apps.presupuesto.api.formulacion_views import _responsable
        r = _responsable(self.f)
        self.assertIsNone(r["id"])
        self.assertTrue(r["motivo"])

    def test_el_encargado_tiene_que_ser_del_area(self):
        """Sin esta guarda, cambiar un número en la petición le asigna una
        formulación a alguien de otra área."""
        from django.conf import settings
        from django.test import Client
        if self.user is None or not self.ajenos:
            self.skipTest("faltan datos para el cruce")
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        c = Client(HTTP_HOST=host)
        c.force_login(self.user)
        r = c.patch(f"/presupuesto/api/formulaciones/{self.f.id}/responsable/",
                    {"funcionario_id": self.ajenos[0].id}, content_type="application/json")
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_asignar_y_quitar_queda_auditado(self):
        from django.conf import settings
        from django.test import Client
        from apps.presupuesto.models.auditoria import AuditoriaDato
        if self.user is None or not self.propios:
            self.skipTest("el área no tiene funcionarios")
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        c = Client(HTTP_HOST=host)
        c.force_login(self.user)
        r = c.patch(f"/presupuesto/api/formulaciones/{self.f.id}/responsable/",
                    {"funcionario_id": self.propios[0].id}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["responsable"]["id"], self.propios[0].id)

        r = c.patch(f"/presupuesto/api/formulaciones/{self.f.id}/responsable/",
                    {"funcionario_id": None}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["responsable"]["id"])

        filas = AuditoriaDato.objects.filter(entidad="formulacion",
                                             entidad_id=self.f.id, campo="responsable")
        self.assertEqual(filas.count(), 2, "asignar y quitar tienen que dejar rastro")

    def test_el_area_sin_funcionarios_lo_explica_en_vez_de_ofrecer_la_nada(self):
        """Un desplegable vacío sobre la nada culpa al usuario de algo que no es
        suyo. Es la lección del selector de responsables de evento."""
        from apps.presupuesto.api.formulacion_views import _funcionarios_de
        from apps.login.models.funcionario import Subgrupo
        vacios = [s.id for s in Subgrupo.objects.all()
                  if not _funcionarios_de(s.id)]
        if not vacios:
            self.skipTest("todos los subgrupos tienen funcionarios")
        # El motivo lo arma la vista; acá se comprueba que la lista sí viene vacía
        # y que por tanto hay que explicarlo.
        self.assertEqual(_funcionarios_de(vacios[0]), [])


class SoportesTests(unittest.TestCase):
    """Los soportes del expediente. **Estos tests escriben en MONGO**, que no
    entra en la transacción de Postgres, así que cada uno borra su blob a mano.

    Lo que se protege es que un requisito no pueda quedar «cumplido» sin la
    prueba que lo sostiene, y que no entre cualquier archivo a un expediente
    público.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()

    def setUp(self):
        from apps.documentos.services import mongo_storage
        from apps.presupuesto.models import ActividadPlan
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")
        if not ActividadPlan.objects.filter(id=ACTIVIDAD_BANCO).exists():
            self.skipTest("la actividad del Banco ya no está en esta base")
        try:
            if not mongo_storage.ping():
                self.skipTest("Mongo no responde")
        except Exception:
            self.skipTest("Mongo no está configurado en este entorno")
        self.mongo_ids = []
        self.f = Formulacion.objects.create(
            actividad_plan_id=ACTIVIDAD_BANCO, vigencia_id=VIGENCIA_PRUEBA,
            subgrupo_id=SUBGRUPO_DEPORTE, objeto="ZZZ_PRUEBA_BORRAR — soportes",
            estado_id=1, estado_fecha=timezone.now(), creado_en=timezone.now())

    def tearDown(self):
        from apps.documentos.services import mongo_storage
        from apps.presupuesto.models import DocumentoFormulacion
        from apps.presupuesto.models.auditoria import AuditoriaDato
        f = getattr(self, "f", None)
        if f is None:
            return
        for mid in DocumentoFormulacion.objects.filter(
                formulacion=f).values_list("mongo_id", flat=True):
            if mid:
                self.mongo_ids.append(mid)
        for mid in set(self.mongo_ids):
            try:
                mongo_storage.borrar(mid)
            except Exception:
                pass
        RequisitoCumplido.objects.filter(formulacion=f).delete()
        DocumentoFormulacion.objects.filter(formulacion=f).delete()
        AuditoriaDato.objects.filter(entidad="formulacion", entidad_id=f.id).delete()
        Formulacion.objects.filter(id=f.id).delete()

    def _cliente(self):
        from django.conf import settings
        from django.test import Client
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        c = Client(HTTP_HOST=host)
        c.force_login(self.user)
        return c

    @staticmethod
    def _pdf():
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(
            "estudios_previos.pdf",
            b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF",
            content_type="application/pdf")

    def test_el_soporte_va_y_vuelve_identico(self):
        """El cifrado no puede alterar el archivo: un estudio previo que vuelve
        distinto no sirve como prueba de nada."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        c = self._cliente()
        original = self._pdf()
        contenido = original.read()
        original.seek(0)
        r = c.post(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/",
                   {"archivo": original})
        self.assertEqual(r.status_code, 201, r.content[:200])
        doc_id = r.json()["documento"]["id"]
        r = c.get(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/{doc_id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, contenido)

    def test_subir_contra_un_requisito_lo_marca_y_lo_enlaza(self):
        """`exige_evidencia` está en 8 de los 16: sin esto esa marca no se
        puede cumplir."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        c = self._cliente()
        r = c.post(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/",
                   {"archivo": self._pdf(), "requisito_codigo": "estudios_previos"})
        self.assertEqual(r.status_code, 201, r.content[:200])
        rc = RequisitoCumplido.objects.get(formulacion=self.f,
                                           requisito_id="estudios_previos")
        self.assertEqual(rc.estado, "ok")
        self.assertEqual(rc.documento_id, r.json()["documento"]["id"])

    def test_borrar_el_soporte_devuelve_el_requisito_a_pendiente(self):
        """Dejarlo en «cumplido» sin soporte sería afirmar algo que ya no se
        puede probar."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        c = self._cliente()
        r = c.post(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/",
                   {"archivo": self._pdf(), "requisito_codigo": "estudios_previos"})
        doc_id = r.json()["documento"]["id"]
        r = c.delete(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/{doc_id}/")
        self.assertEqual(r.status_code, 200)
        rc = RequisitoCumplido.objects.get(formulacion=self.f,
                                           requisito_id="estudios_previos")
        self.assertEqual(rc.estado, "pendiente")
        self.assertIsNone(rc.documento_id)

    def test_no_entra_cualquier_archivo(self):
        """Lista blanca: es un expediente público, no un disco compartido."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        if self.user is None:
            self.skipTest("no hay superusuario")
        c = self._cliente()
        casos = [
            ("virus.exe", b"MZ", "application/x-msdownload", "un ejecutable"),
            ("falso.pdf", b"x", "image/png", "extensión que no cuadra con el tipo"),
            ("vacio.pdf", b"", "application/pdf", "un archivo vacío"),
        ]
        for nombre, datos, mime, que_es in casos:
            with self.subTest(caso=que_es):
                r = c.post(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/",
                           {"archivo": SimpleUploadedFile(nombre, datos, content_type=mime)})
                self.assertEqual(r.status_code, 400, f"entró {que_es}")

    def test_un_soporte_no_se_alcanza_desde_otra_formulacion(self):
        """La URL lleva las dos llaves y tienen que corresponder."""
        if self.user is None:
            self.skipTest("no hay superusuario")
        c = self._cliente()
        r = c.post(f"/presupuesto/api/formulaciones/{self.f.id}/documentos/",
                   {"archivo": self._pdf()})
        doc_id = r.json()["documento"]["id"]
        otra = Formulacion.objects.exclude(id=self.f.id).first()
        if otra is None:
            self.skipTest("no hay otra formulación con la que cruzar")
        r = c.get(f"/presupuesto/api/formulaciones/{otra.id}/documentos/{doc_id}/")
        self.assertEqual(r.status_code, 404)


class FormulacionEnElExpedienteTests(unittest.TestCase):
    """La formulación tiene que verse DENTRO de la meta, antes de sus contratos.

    Es el §7 del plan: en el ciclo la formulación ocurre antes que el contrato,
    y la pantalla tiene que leerse en ese orden. Acá se protege que el dato
    llegue —el orden visual lo fija la plantilla— y, sobre todo, que llegue por
    la MISMA cadena que ya usan los contratos: actividad → indicador → meta.
    Una vía nueva para la misma pregunta acabaría dando otra respuesta.
    """

    def setUp(self):
        if not _hay_dominio():
            self.skipTest("el DDL 019 no está aplicado en esta base")

    def test_cada_formulacion_llega_a_su_meta(self):
        from apps.presupuesto.services.expediente_proyecto import (
            expediente_lista, expediente_proyecto,
        )
        vistas = set()
        for p in expediente_lista()["proyectos"]:
            for m in expediente_proyecto(p["id"]).get("metas", []):
                for f in (m.get("formulaciones") or []):
                    vistas.add(f["id"])
                    self.assertIn("codigo", f)
                    self.assertIn("vigencia", f)
                    # `null` = sin dato. Un 0 diría «vale cero pesos».
                    self.assertIn("valor_estimado", f)
        # Las que DEBERÍAN verse, por la misma cadena que usan los contratos.
        # Una formulación cuya actividad no tiene indicador no llega a ninguna
        # meta, y eso es correcto: lo que no puede pasar es perder una que sí.
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT f.id
                FROM formulacion f
                JOIN actividad_indicador ai ON ai.actividad_plan_id = f.actividad_plan_id
                                           AND ai.activo
            """)
            esperadas = {r[0] for r in cur.fetchall()}
        if not esperadas:
            self.skipTest("ninguna formulación cuelga de una actividad con indicador")
        self.assertEqual(vistas, esperadas,
                         "el expediente perdió formulaciones que sí llegan a una meta")

    def test_el_expediente_no_revienta_sin_el_dominio(self):
        """`_formulaciones_por_meta` consulta si la tabla existe antes de leerla:
        en un entorno sin el DDL 019 el expediente tiene que seguir abriéndose,
        no fallar por una sección que aún no aplica."""
        from apps.presupuesto.services.expediente_proyecto import _formulaciones_por_meta
        from django.db import connection
        with connection.cursor() as cur:
            self.assertIsInstance(_formulaciones_por_meta(cur), dict)
