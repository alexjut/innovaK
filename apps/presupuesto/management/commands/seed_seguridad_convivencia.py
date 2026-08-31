"""
Siembra la CADENA PRESUPUESTAL del subgrupo "Seguridad" (id=38, dependencia
INVERSIÓN LOCAL id=3) para los 3 proyectos nuevos del sector.

Cadena obligatoria sembrada (SIN Eventos, SIN tipo_evento):

    Proyecto -> MetaProyectoBD -> Meta (MetaBD, catálogo) -> Indicador (KPI)
                                                                 ^
                                          ActividadPlan -> ActividadIndicador

    Cadena financiera (aparte):
        Cdp -> Contrato (cdp_id) -> ContratoActividadPlan

Catálogos (Objetivo / Programa / Vigencia / Area) se resuelven con
find-or-create PREFIRIENDO el match existente por texto/código.

IMPORTANTE:
- Todos los modelos son managed=False (BD externa). Este comando NO crea
  schema; solo inserta filas vía ORM.
- Idempotente: get_or_create por claves naturales. Re-ejecutable sin duplicar.
- --dry-run es el DEFAULT (no escribe). --commit escribe dentro de
  transaction.atomic().
- Donde NO hay dato real (CDP número, valor de contrato, SIPSE) se deja NULL
  y se reporta. NO se inventan números.

Mapeo ActividadPlan -> tipo_evento (SOLO metadato, NO se crean eventos aquí):
  2688 M1 fortalecer orgs        -> CULTURA_ORG
  2688 M2 acciones formativas    -> CAPACITACION
  2688 M3 iniciativas convivencia-> PENDIENTE FORK (BANCO_INICIATIVAS vs PROYECTO_CULTURAL)
  2688 entrega equipos           -> ENTREGA
  2745 M1/M2                      -> CAPACITACION / CURSO
  2745 M3/M7                      -> PROYECTO_CULTURAL
  2745 M5                         -> CAPACITACION
  2745 M6 (150 ciudadanos)        -> CARACTERIZACION / participantes
  2706/998 motos                 -> ENTREGA institucional (PENDIENTE FORK)
  2706/1078 Casa de Justicia     -> ENTREGA equipamiento (PENDIENTE FORK)
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.login.models import Subgrupo
from apps.presupuesto.models.core import Proyecto, ActividadPlan, Contrato
from apps.presupuesto.models.core_catalogos import Objetivo, Programa, Vigencia, Area
from apps.presupuesto.models.indicadores import (
    MetaBD, MetaProyectoBD, Indicador, ActividadIndicador,
)
from apps.presupuesto.models.sql import Cdp, ContratoActividadPlan


# Subgrupo reutilizado (ya existe en BD). Ver REPORTE: nombre actual = "Seguridad".
SUBGRUPO_ID = 38
DEPENDENCIA_ID = 3
AREA_NOMBRE = "Seguridad"          # area.id=9 ya existe
VIGENCIA_ANIO = 2025               # vigencia.codigo=2025 / id=6 ya existe


# ----------------------------------------------------------------------------
# DATA normalizada (4 pestañas = 3 proyectos)
# ----------------------------------------------------------------------------
# Cada meta: (descripcion, magnitud_vig_2025, valor_2025, unidad, tipo_evento_hint)
PROYECTOS = [
    {
        "codigo": "2688",
        "nombre": "KENNEDY CAMINA SEGURA",
        "objetivo": "Bogotá Avanza en Seguridad",
        "programa": ("Programa 1. Diálogo social y cultura ciudadana para la "
                     "convivencia pacífica"),
        "sipse": "141794",
        "valor_total": Decimal("2291500000"),
        "metas": [
            ("Fortalecer 100 organizaciones comunitarias", Decimal("25"),
             Decimal("916600000"), "organizaciones", "CULTURA_ORG"),
            ("Implementar 4 acciones formativas diferenciales", Decimal("1"),
             Decimal("687450000"), "acciones", "CAPACITACION"),
            ("Implementar 40 iniciativas de convivencia", Decimal("10"),
             Decimal("687450000"), "iniciativas",
             "PENDIENTE_FORK(BANCO_INICIATIVAS|PROYECTO_CULTURAL)"),
        ],
        # Un contrato sin valor (NULL -> reportar)
        "contratos": [
            {"tipo": "CPS", "numero": 983, "vigencia": 2025,
             "valor": None, "sipse": "141794",
             "objeto": "KENNEDY CAMINA SEGURA — convenio 983-2025"},
        ],
    },
    {
        "codigo": "2745",
        "nombre": "KENNEDY CAMINA HACIA LA CONVIVENCIA",
        "objetivo": "Bogotá Avanza en Seguridad",
        "programa": "Programa 4: Servicios centrados en la justicia",
        "sipse": "143065",
        "valor_total": Decimal("2535280000"),
        # 2745: la data NO distingue PDD vs vig-2025. Se usa el MISMO número
        # como general (en el nombre de MetaBD) y como KPI vig 2025.
        # ALEX DEBE CONFIRMAR las magnitudes vig-2025 reales (ver HUECOS).
        "metas": [
            ("Ejecutar 1 programa comunitario con enfoque restaurativo", Decimal("1"),
             Decimal("380292000"), "programas", "CAPACITACION|CURSO"),
            ("Implementar 1 acción pedagógica", Decimal("1"),
             Decimal("253528000"), "acciones", "CAPACITACION|CURSO"),
            ("Implementar 3 proyectos comunitarios CNSCC", Decimal("3"),
             Decimal("253528000"), "proyectos", "PROYECTO_CULTURAL"),
            ("Fortalecer 1 programa de conflictividad escolar", Decimal("1"),
             Decimal("507056000"), "programas", "CAPACITACION"),
            ("Fortalecer 50 actores comunitarios", Decimal("50"),
             Decimal("507056000"), "actores", "CAPACITACION"),
            ("Beneficiar 150 ciudadanos", Decimal("150"),
             Decimal("380292000"), "ciudadanos", "CARACTERIZACION|participantes"),
            ("Implementar 2 proyectos de justicia local", Decimal("2"),
             Decimal("253528000"), "proyectos", "PROYECTO_CULTURAL"),
        ],
        "contratos": [
            {"tipo": "CPS", "numero": 1001, "vigencia": 2025,
             "valor": None, "sipse": "143065",
             "objeto": "KENNEDY CAMINA HACIA LA CONVIVENCIA — convenio 1001-2025"},
        ],
    },
    {
        # HIPÓTESIS: 998 y 1078 son el MISMO proyecto 2706 (2 contratos).
        # Nombre canónico tomado del objetivo del 2706 (pestaña 998 traía
        # "Kennedy Camina Segura" — se trata como error de pestaña). CONFIRMAR.
        "codigo": "2706",
        "nombre": "KENNEDY EN ALIANZA POR LA SEGURIDAD",
        "objetivo": "Kennedy en alianza por la seguridad",
        "programa": ("Programa 3. Desmantelamiento de estructuras criminales y "
                     "delincuenciales con mejores capacidades y activos "
                     "tecnológicos."),
        "sipse": None,
        "valor_total": None,
        # 2706: MetaBD = 4 (PDD cuatrienio) en el nombre; KPI vig 2025 = 1.
        "metas": [
            # Contrato 998 — dotación organismos (PDD: 4 dotaciones; vig 2025: 1 = 36 motos Policía)
            ("Suministrar dotación a 4 organismos de seguridad (vig 2025: 36 motos Policía)",
             Decimal("1"), None, "dotaciones",
             "ENTREGA institucional PENDIENTE_FORK"),
            # Contrato 1078 — equipamiento (PDD: 4 intervenciones; vig 2025: 1 = Casa de Justicia)
            ("Intervenir 4 equipamientos de seguridad y justicia (vig 2025: Casa de Justicia)",
             Decimal("1"), None, "intervenciones",
             "ENTREGA equipamiento PENDIENTE_FORK"),
        ],
        "contratos": [
            {"tipo": "SUBASTA", "numero": 998, "vigencia": 2025,
             "valor": Decimal("2058504840"),  # base 1.887.000.000 + adición 171.504.840
             "sipse": None,  # FALTA VALIDAR
             "objeto": "Dotación organismos de seguridad — 36 motos (998, subasta inversa)"},
            {"tipo": "CPS", "numero": 1078, "vigencia": 2025,
             "valor": Decimal("59457606"),
             "sipse": "144388",
             "objeto": "Intervención Casa de Justicia — dotación (1078)"},
        ],
    },
]


class Reporte:
    def __init__(self):
        self.lineas = []
        self.huecos = []
        self.catalogos_match = []
        self.catalogos_faltan = []

    def add(self, accion, detalle):
        self.lineas.append(f"  [{accion}] {detalle}")

    def hueco(self, detalle):
        self.huecos.append(f"  - {detalle}")

    def cat_match(self, detalle):
        self.catalogos_match.append(f"  ✓ {detalle}")

    def cat_falta(self, detalle):
        self.catalogos_faltan.append(f"  ✗ {detalle}")


class Command(BaseCommand):
    help = ("Siembra la cadena presupuestal del subgrupo Seguridad "
            "(3 proyectos nuevos). --dry-run por defecto.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit", action="store_true",
            help="Escribe en BD. Sin esto corre en modo --dry-run (no escribe).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="No escribe (DEFAULT). Simula con savepoint+rollback.",
        )

    def handle(self, *args, **opts):
        commit = opts.get("commit", False)
        rep = Reporte()

        modo = "COMMIT (ESCRIBE)" if commit else "DRY-RUN (NO escribe)"
        self.stdout.write(self.style.WARNING(f"\n=== seed_seguridad_convivencia — modo {modo} ===\n"))

        # Todo dentro de un atomic. En dry-run hacemos rollback al final.
        try:
            with transaction.atomic():
                self._sembrar(rep, commit)
                if not commit:
                    # Forzar rollback del savepoint: nada se persiste.
                    raise _Rollback()
        except _Rollback:
            pass

        self._imprimir_reporte(rep, commit)

    # ------------------------------------------------------------------
    def _sembrar(self, rep, commit):
        # --- Subgrupo (reutilizado, NO se crea) ---
        sub = Subgrupo.objects.filter(id=SUBGRUPO_ID).first()
        if sub:
            rep.add("USA", f"Subgrupo id={sub.id} '{sub.nombre}' "
                           f"(dependencia_id={sub.dependencia_id})")
            if sub.nombre.strip().lower() != "seguridad y convivencia":
                rep.hueco(f"El subgrupo id=38 se llama '{sub.nombre}', NO "
                          f"'Seguridad y Convivencia'. CONFIRMAR con Alex si se "
                          f"reusa tal cual o se renombra.")
        else:
            rep.add("ERROR", f"Subgrupo id={SUBGRUPO_ID} no existe. No se puede continuar.")
            return

        # --- Area (find por nombre) ---
        area = Area.objects.filter(nombre__iexact=AREA_NOMBRE).first()
        if area:
            rep.cat_match(f"Area '{area.nombre}' (id={area.id}) — match")
        else:
            rep.cat_falta(f"Area '{AREA_NOMBRE}' no encontrada. Se omite (no es FK "
                          f"de la cadena Proyecto).")

        # --- Vigencia 2025 (find por codigo) ---
        vig = Vigencia.objects.filter(codigo=VIGENCIA_ANIO).first()
        if vig:
            rep.cat_match(f"Vigencia {VIGENCIA_ANIO} (id={vig.id}, codigo={vig.codigo}) — match")
        else:
            rep.cat_falta(f"Vigencia {VIGENCIA_ANIO} no encontrada. Programa requiere "
                          f"vigencia (PROTECT) — NO se podrán crear programas.")

        for p in PROYECTOS:
            self._sembrar_proyecto(rep, commit, p, sub, vig)

    # ------------------------------------------------------------------
    def _sembrar_proyecto(self, rep, commit, p, sub, vig):
        rep.add("PROYECTO", f"--- {p['codigo']} {p['nombre']} ---")

        # ---- Objetivo (find-or-create por nombre) ----
        objetivo = Objetivo.objects.filter(nombre__iexact=p["objetivo"]).first()
        if objetivo:
            rep.cat_match(f"Objetivo '{p['objetivo']}' (id={objetivo.id}) — match")
        else:
            rep.cat_falta(f"Objetivo '{p['objetivo']}' NO existe (solo hay 4 de "
                          f"prueba en BD). Se CREARÍA.")
            if commit:
                objetivo = Objetivo.objects.create(nombre=p["objetivo"])
                rep.add("CREA", f"Objetivo '{objetivo.nombre}' id={objetivo.id}")

        # ---- Programa (find-or-create por nombre) ----
        programa = Programa.objects.filter(nombre__iexact=p["programa"]).first()
        if programa:
            rep.cat_match(f"Programa '{p['programa'][:50]}...' (id={programa.id}) — match")
        else:
            rep.cat_falta(f"Programa '{p['programa'][:60]}...' NO existe. Se CREARÍA "
                          f"(requiere vigencia {VIGENCIA_ANIO}).")
            if commit:
                if vig is None:
                    rep.add("OMITE", "Programa no creado: falta Vigencia (PROTECT).")
                else:
                    programa = Programa.objects.create(
                        nombre=p["programa"],
                        vigencia=vig,
                        objetivo=objetivo if objetivo else None,
                    )
                    rep.add("CREA", f"Programa '{programa.nombre[:40]}' id={programa.id}")

        # ---- Proyecto (get_or_create por codigo) ----
        # proyecto.id es GENERATED ALWAYS AS IDENTITY -> NO pasar id (AutoField lo omite).
        # nombre_ci es columna generada -> NO insertar.
        proyecto = Proyecto.objects.filter(codigo=p["codigo"]).first()
        if proyecto:
            rep.add("EXISTE", f"Proyecto codigo={p['codigo']} ya en BD (id={proyecto.id})")
        else:
            rep.add("CREARÍA", f"Proyecto codigo={p['codigo']} nombre='{p['nombre']}' "
                               f"subgrupo_id={sub.id} programa_id="
                               f"{getattr(programa, 'id', None)}")
            if commit:
                proyecto = Proyecto.objects.create(
                    codigo=p["codigo"],
                    nombre=p["nombre"],
                    subgrupo=sub,
                    programa=programa if programa else None,
                )
                rep.add("CREA", f"Proyecto id={proyecto.id} codigo={proyecto.codigo}")

        if p["sipse"]:
            rep.add("DATO", f"SIPSE proyecto {p['codigo']} = {p['sipse']} "
                            f"(no hay columna SIPSE en `proyecto` -> solo anotado)")
        else:
            rep.hueco(f"SIPSE del proyecto {p['codigo']} desconocido.")

        # En dry-run sin proyecto persistido no podemos colgar hijos reales;
        # reportamos lo que se haría. En commit, proyecto existe.
        proyecto_ref = proyecto

        # ---- Metas + MetaProyecto + Indicador + ActividadPlan + ActividadIndicador ----
        for (desc, magnitud, valor, unidad, hint) in p["metas"]:
            self._sembrar_meta(rep, commit, proyecto_ref, p["codigo"],
                               desc, magnitud, valor, unidad, hint)

        # ---- Cadena financiera: CDP -> Contrato -> ContratoActividadPlan ----
        for cdef in p["contratos"]:
            self._sembrar_contrato(rep, commit, proyecto_ref, p, cdef)

    # ------------------------------------------------------------------
    def _sembrar_meta(self, rep, commit, proyecto, proy_codigo,
                      desc, magnitud, valor, unidad, hint):
        # MetaBD: catálogo. find por nombre exacto.
        meta = MetaBD.objects.filter(nombre__iexact=desc).first()
        if meta:
            rep.add("EXISTE", f"Meta '{desc[:50]}' (codigo={meta.codigo})")
        else:
            rep.add("CREARÍA", f"Meta '{desc[:55]}'  [unidad={unidad}]")
            if commit:
                meta = self._crear_meta(desc)
                rep.add("CREA", f"Meta codigo={meta.codigo}")

        valor_txt = f"${valor:,.0f}" if valor is not None else "NULL"
        mag_txt = str(magnitud) if magnitud is not None else "NULL"
        rep.add("META-VIG", f"   2025: magnitud={mag_txt}, valor={valor_txt}, "
                            f"hint_tipo_evento={hint}")
        if valor is None:
            rep.hueco(f"Valor 2025 de meta '{desc[:40]}' (proy {proy_codigo}) sin dato.")

        # Si no hay proyecto persistido (dry-run sobre proyecto nuevo), igual
        # describimos toda la cadena hija que se crearía al --commit.
        proy_ref = proyecto.id if proyecto else f"<proyecto {proy_codigo} nuevo>"
        meta_ref = meta.codigo if meta else f"<meta '{desc[:25]}' nueva>"

        # MetaProyecto (asociación) — get_or_create por (meta, proyecto)
        mp = (MetaProyectoBD.objects.filter(meta=meta, proyecto=proyecto).first()
              if (proyecto and meta) else None)
        if mp:
            rep.add("EXISTE", f"   MetaProyecto meta={meta_ref}↔proy={proy_ref}")
        else:
            rep.add("CREARÍA", f"   MetaProyecto meta={meta_ref}↔proy={proy_ref}")
            if commit and proyecto and meta:
                mp = MetaProyectoBD.objects.create(meta=meta, proyecto=proyecto)
                rep.add("CREA", f"   MetaProyecto id={mp.id}")

        # Indicador (KPI) — uno por meta. find por (meta_proyecto, nombre)
        ind = (Indicador.objects.filter(meta_proyecto=mp, nombre=desc).first()
               if mp else None)
        if ind:
            rep.add("EXISTE", f"   Indicador KPI id={ind.id} mag={ind.meta_magnitud}")
        else:
            rep.add("CREARÍA", f"   Indicador KPI '{desc[:38]}' mag={mag_txt} {unidad} "
                               f"(SUMA)")
            if commit and mp:
                ind = Indicador.objects.create(
                    meta_proyecto=mp,
                    nombre=desc,
                    unidad_medida=unidad,
                    meta_magnitud=magnitud if magnitud is not None else Decimal("0"),
                    tipo_agregacion="SUMA",
                )
                rep.add("CREA", f"   Indicador KPI id={ind.id} mag={ind.meta_magnitud}")

        # ActividadPlan (una por meta) — get_or_create por (proyecto, descripcion)
        ap = (ActividadPlan.objects.filter(proyecto=proyecto, descripcion=desc).first()
              if proyecto else None)
        if ap:
            rep.add("EXISTE", f"   ActividadPlan #{ap.id}")
        else:
            rep.add("CREARÍA", f"   ActividadPlan '{desc[:42]}' "
                               f"[mapea a tipo_evento: {hint}]")
            if commit and proyecto:
                ap = ActividadPlan.objects.create(proyecto=proyecto, descripcion=desc)
                rep.add("CREA", f"   ActividadPlan #{ap.id}")

        # ActividadIndicador (vínculo ActividadPlan↔KPI)
        ai = (ActividadIndicador.objects.filter(actividad_plan=ap, indicador=ind).first()
              if (ap and ind) else None)
        if ai:
            rep.add("EXISTE", f"   ActividadIndicador ap={ap.id}↔ind={ind.id}")
        else:
            rep.add("CREARÍA", "   ActividadIndicador (ActividadPlan↔KPI)")
            if commit and ap and ind:
                ActividadIndicador.objects.create(actividad_plan=ap, indicador=ind)
                rep.add("CREA", f"   ActividadIndicador ap={ap.id}↔ind={ind.id}")

    def _crear_meta(self, desc):
        """Crea MetaBD. `metas.codigo` no tiene DEFAULT pese a la secuencia
        `metas_codigo_seq` -> el create plano (AutoField omite codigo) fallaría
        con NULL. Fallback: nextval explícito."""
        from django.db import IntegrityError
        from django.db import transaction as _tx
        try:
            with _tx.atomic():
                return MetaBD.objects.create(nombre=desc, descripcion=desc)
        except IntegrityError as exc:
            if 'null value in column "codigo"' not in str(exc):
                raise
        with connection.cursor() as c:
            c.execute("SELECT nextval('metas_codigo_seq')")
            next_cod = c.fetchone()[0]
        m = MetaBD(codigo=next_cod, nombre=desc, descripcion=desc)
        m.save(force_insert=True)
        return m

    # ------------------------------------------------------------------
    def _sembrar_contrato(self, rep, commit, proyecto, p, cdef):
        numero = cdef["numero"]
        vigencia = cdef["vigencia"]
        valor = cdef["valor"]
        valor_txt = f"${valor:,.0f}" if valor is not None else "NULL"

        # --- CDP --- NO hay número de CDP real -> dejar numero/valor NULL y reportar.
        rep.hueco(f"CDP del contrato {cdef['tipo']}-{numero}-{vigencia} "
                  f"(proy {p['codigo']}): número y valor de CDP desconocidos -> NULL.")

        cdp = None
        if proyecto:
            # find: ¿ya hay un CDP placeholder de este proyecto sin número?
            # Para idempotencia, identificamos por objeto.
            cdp_obj = f"CDP placeholder — {p['codigo']} contrato {numero}/{vigencia}"
            cdp = Cdp.objects.filter(proyecto=proyecto, objeto=cdp_obj).first()
            if cdp:
                rep.add("EXISTE", f"CDP placeholder id={cdp.id} (proy {p['codigo']})")
            else:
                rep.add("CREARÍA", f"CDP placeholder (numero=NULL, valor=NULL) "
                                   f"proy={proyecto.id} '{cdp_obj}'")
                if commit:
                    cdp = Cdp.objects.create(
                        proyecto=proyecto,
                        numero=None,
                        valor=None,
                        objeto=cdp_obj,
                        descripcion=cdp_obj,
                    )
                    rep.add("CREA", f"CDP id={cdp.id}")

        # --- Contrato --- get_or_create por (contrato_numero, contrato_vigencia)
        contrato = Contrato.objects.filter(
            contrato_numero=numero, contrato_vigencia=vigencia).first()
        if contrato:
            rep.add("EXISTE", f"Contrato {cdef['tipo']}-{numero}-{vigencia} (id={contrato.id})")
        else:
            rep.add("CREARÍA", f"Contrato {cdef['tipo']}-{numero}-{vigencia} valor={valor_txt} "
                               f"cdp_id={getattr(cdp,'id',None)} objeto='{cdef['objeto'][:40]}'")
            if commit:
                contrato = self._crear_contrato(cdef, cdp)
                rep.add("CREA", f"Contrato id={contrato.id} {cdef['tipo']}-{numero}-{vigencia}")

        if valor is None:
            rep.hueco(f"Valor del contrato {cdef['tipo']}-{numero}-{vigencia} sin dato "
                      f"(proy {p['codigo']}). NO se valida saldo CDP.")
        if cdef.get("sipse") is None:
            rep.hueco(f"SIPSE del contrato {numero}/{vigencia} (proy {p['codigo']}) sin dato.")

        # --- ContratoActividadPlan --- vincula contrato a cada ActividadPlan del proyecto.
        # monto=0 (no hay desglose real). Reglas: Σ monto ≤ contrato.valor;
        # si valor NULL no se fuerza la validación (solo se anota).
        if commit and contrato and proyecto:
            aps = ActividadPlan.objects.filter(proyecto=proyecto)
            for ap in aps:
                cap = ContratoActividadPlan.objects.filter(
                    contrato=contrato, actividad_plan=ap).first()
                if not cap:
                    ContratoActividadPlan.objects.create(
                        contrato=contrato, actividad_plan=ap, monto=Decimal("0"))
                    rep.add("CREA", f"   ContratoActividadPlan c={contrato.id}↔ap={ap.id} monto=0")
        else:
            rep.add("CREARÍA", f"   ContratoActividadPlan: contrato {numero} ↔ cada "
                               f"ActividadPlan del proyecto (monto=0)")

    def _crear_contrato(self, cdef, cdp):
        """Crea el contrato con id explícito.

        NO es que falte la secuencia: `contrato.id` es identity y la tiene
        (corregido 2026-08-27, ver models/core.py:127). Es el patrón heredado
        de cuando se creía lo contrario. Ojo: un id explícito NO avanza la
        secuencia.
        """
        next_id = (Contrato.objects.all().order_by("-id").values_list("id", flat=True).first() or 0) + 1
        contrato = Contrato(
            id=next_id,
            contrato_tipo=cdef["tipo"],
            contrato_numero=cdef["numero"],
            contrato_vigencia=cdef["vigencia"],
            objeto=cdef["objeto"],
            valor=cdef["valor"],
            cdp=cdp,
        )
        contrato.save(force_insert=True)
        return contrato

    # ------------------------------------------------------------------
    def _imprimir_reporte(self, rep, commit):
        w = self.stdout.write
        w("\n" + "=" * 70)
        w("REPORTE — cadena presupuestal Seguridad")
        w("=" * 70)

        w("\n-- CATÁLOGOS QUE HICIERON MATCH --")
        for l in rep.catalogos_match or ["  (ninguno)"]:
            w(l)
        w("\n-- CATÁLOGOS QUE FALTAN / SE CREARÍAN --")
        for l in rep.catalogos_faltan or ["  (ninguno)"]:
            w(l)

        w("\n-- ACCIONES (lo que se crearía / encontró) --")
        for l in rep.lineas:
            w(l)

        w("\n-- HUECOS QUE ALEX DEBE CONFIRMAR ANTES DEL COMMIT --")
        for l in rep.huecos or ["  (ninguno)"]:
            w(l)

        w("\n" + "=" * 70)
        if commit:
            w(self.style.SUCCESS("COMMIT aplicado (transacción confirmada)."))
        else:
            w(self.style.WARNING("DRY-RUN: nada se escribió en la BD. "
                                 "Re-ejecuta con --commit para aplicar."))
        w("=" * 70 + "\n")


class _Rollback(Exception):
    """Señal interna para abortar el atomic en dry-run sin persistir."""
    pass
