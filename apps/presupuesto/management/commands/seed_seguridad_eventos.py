"""
Siembra los EVENTOS de captura del subgrupo "Seguridad" (id=38), uno por
ActividadPlan ya existente en BD (114-125), con su tipo_evento resuelto.

Cadena (este comando solo crea la última capa, Evento):

    Proyecto -> MetaProyecto -> Indicador (KPI)
                                    ^
            ActividadPlan -> ActividadIndicador
                  ^
               Evento  <-- ESTO crea este comando

Reglas:
- managed=False (BD externa). NO crea schema; solo inserta filas vía ORM.
- NO escribe en `actividad_plan` (el tipo_evento vive en `evento`).
- Idempotente: get_or_create por clave natural
  (actividad_plan_id, tipo_evento_codigo, nombre).
- --dry-run es el DEFAULT (no escribe). --commit escribe dentro de
  transaction.atomic().
- `evento.id` se llena por DEFAULT nextval('evento_id_seq') en BD; no se
  pasa id explícito.
- El KPI ligado se resuelve vía `actividad_indicador.indicador_id` de la
  ActividadPlan; magnitud_aportada=0.
- Eventos sin coordenadas -> lugar_incidencia_id=100055 (la Alcaldía).

Mapeo RESUELTO por Alex (ActividadPlan -> tipo_evento). La ap 121 lleva
DOS eventos (CARACTERIZACION + CAPACITACION). Total = 13 eventos.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.login.models import Evento
from apps.login.models.evento import TipoEvento
from apps.presupuesto.models.core import ActividadPlan
from apps.presupuesto.models.indicadores import ActividadIndicador
from apps.georeferenciacion.models import LugarIncidencia


SUBGRUPO_ID = 38
DEPENDENCIA_ID = 3
LUGAR_INCIDENCIA_ID = 100055
FECHA_INICIO = "2025-01-01"
VIGENCIA = "2025"

# (actividad_plan_id, tipo_evento_codigo, sufijo_nombre|None, sector_caract|None)
# sufijo_nombre solo se usa para diferenciar los 2 eventos de la ap 121.
MAPEO = [
    (114, "CULTURA_ORG",       None,            None),
    (115, "CAPACITACION",      None,            None),
    (116, "BANCO_INICIATIVAS", None,            None),
    (117, "CAPACITACION",      None,            None),
    (118, "CAPACITACION",      None,            None),
    (119, "PROYECTO_CULTURAL", None,            None),
    (120, "CAPACITACION",      None,            None),
    (121, "CARACTERIZACION",   "Caracterización", "seguridad"),
    (121, "CAPACITACION",      "Capacitación",  None),
    (122, "CARACTERIZACION",   None,            "seguridad"),
    (123, "PROYECTO_CULTURAL", None,            None),
    (124, "ENTREGA",           None,            None),
    (125, "ENTREGA",           None,            None),
]

TIPOS_USADOS = {m[1] for m in MAPEO}


class Reporte:
    def __init__(self):
        self.eventos = []
        self.huecos = []
        self.followups = []
        self.precheck = []

    def evento(self, d):
        self.eventos.append(d)

    def hueco(self, d):
        self.huecos.append(f"  - {d}")

    def followup(self, d):
        self.followups.append(f"  - {d}")

    def chk(self, d):
        self.precheck.append(f"  {d}")


class Command(BaseCommand):
    help = ("Siembra los eventos de captura del subgrupo Seguridad (uno por "
            "ActividadPlan). --dry-run por defecto.")

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
        self.stdout.write(self.style.WARNING(
            f"\n=== seed_seguridad_eventos — modo {modo} ===\n"))

        try:
            with transaction.atomic():
                self._prechequear(rep)
                self._sembrar(rep, commit)
                if not commit:
                    raise _Rollback()
        except _Rollback:
            pass

        self._imprimir_reporte(rep, commit)

    # ------------------------------------------------------------------
    def _prechequear(self, rep):
        for codigo in sorted(TIPOS_USADOS):
            ok = TipoEvento.objects.filter(codigo=codigo).exists()
            rep.chk(f"tipo_evento '{codigo}': {'EXISTE' if ok else 'FALTA'}")
            if not ok:
                rep.hueco(f"tipo_evento '{codigo}' NO existe en BD. "
                          f"Los eventos de ese tipo NO se crearán.")

        li = LugarIncidencia.objects.filter(id=LUGAR_INCIDENCIA_ID).first()
        rep.chk(f"LugarIncidencia id={LUGAR_INCIDENCIA_ID} (Alcaldía): "
                f"{'EXISTE' if li else 'FALTA'}")
        if li is None:
            rep.hueco(f"LugarIncidencia id={LUGAR_INCIDENCIA_ID} NO existe. "
                      f"Los eventos quedarían sin ubicación en el mapa.")

    # ------------------------------------------------------------------
    def _sembrar(self, rep, commit):
        for ap_id, tipo_codigo, sufijo, sector in MAPEO:
            ap = ActividadPlan.objects.filter(id=ap_id).first()
            if ap is None:
                rep.hueco(f"ActividadPlan id={ap_id} no existe -> evento omitido.")
                continue

            if not TipoEvento.objects.filter(codigo=tipo_codigo).exists():
                continue  # ya reportado en precheck

            indicador_id = (
                ActividadIndicador.objects
                .filter(actividad_plan_id=ap_id)
                .values_list("indicador_id", flat=True)
                .first()
            )

            nombre = self._nombre_evento(ap, sufijo)

            existente = Evento.objects.filter(
                actividad_plan_id=ap_id,
                tipo_evento_id=tipo_codigo,
                nombre=nombre,
            ).first()

            estado = "EXISTE" if existente else "CREARÍA"
            rep.evento({
                "estado": estado,
                "ap_id": ap_id,
                "tipo": tipo_codigo,
                "nombre": nombre,
                "kpi": indicador_id,
                "sector": sector,
                "id": getattr(existente, "id", None),
            })

            if commit and not existente:
                ev = Evento.objects.create(
                    nombre=nombre,
                    tipo_evento_id=tipo_codigo,
                    subgrupo_id=SUBGRUPO_ID,
                    dependencia_id=DEPENDENCIA_ID,
                    actividad_plan_id=ap_id,
                    lugar_incidencia_id=LUGAR_INCIDENCIA_ID,
                    indicador_id=indicador_id,
                    magnitud_aportada=Decimal("0"),
                    sector_caracterizacion=sector,
                    fecha_inicio=FECHA_INICIO,
                    fecha_fin=None,
                    activo=True,
                )
                rep.eventos[-1]["id"] = ev.id
                rep.eventos[-1]["estado"] = "CREÓ"

        # Discrepancia y follow-up documentados.
        rep.hueco(
            "Mapeo de Alex menciona '2688 entrega equipos tecnológicos -> "
            "ENTREGA' pero NO existe una ActividadPlan para eso en el 2688 "
            "(solo 114/115/116). NO se crea ActividadPlan ni evento; Alex "
            "decide si se agrega esa actividad a la cadena."
        )
        rep.followup(
            "Mejorar el tipo_evento ENTREGA para receptor institucional / "
            "equipamiento (ap 124 dotación 36 motos a organismos, ap 125 "
            "Casa de Justicia): hoy ENTREGA asume beneficiario persona; "
            "falta soporte de receptor institucional."
        )

    def _nombre_evento(self, ap, sufijo):
        base = (ap.descripcion or f"ActividadPlan #{ap.id}").strip()
        nombre = f"{base} ({VIGENCIA})"
        if sufijo:
            nombre = f"{base} — {sufijo} ({VIGENCIA})"
        return nombre

    # ------------------------------------------------------------------
    def _imprimir_reporte(self, rep, commit):
        w = self.stdout.write
        w("\n" + "=" * 72)
        w("REPORTE — eventos de captura · subgrupo Seguridad (id=38)")
        w("=" * 72)

        w("\n-- PRE-CHEQUEOS --")
        for l in rep.precheck:
            w(l)

        w(f"\n-- EVENTOS ({len(rep.eventos)}) --")
        for e in rep.eventos:
            kpi = f"KPI {e['kpi']}" if e["kpi"] is not None else "KPI ninguno"
            sec = f" sector={e['sector']}" if e["sector"] else ""
            idtxt = f" id={e['id']}" if e["id"] else ""
            w(f"  [{e['estado']}] ap {e['ap_id']} · {e['tipo']} · {kpi} · "
              f"lugar=Alcaldía(100055){sec}{idtxt}")
            w(f"            nombre: {e['nombre']}")

        w("\n-- HUECOS / DISCREPANCIAS (Alex decide) --")
        for l in rep.huecos or ["  (ninguno)"]:
            w(l)

        w("\n-- FOLLOW-UP --")
        for l in rep.followups or ["  (ninguno)"]:
            w(l)

        w("\n" + "=" * 72)
        if commit:
            w(self.style.SUCCESS("COMMIT aplicado (transacción confirmada)."))
        else:
            w(self.style.WARNING("DRY-RUN: nada se escribió en la BD. "
                                 "Re-ejecuta con --commit para aplicar."))
        w("=" * 72 + "\n")


class _Rollback(Exception):
    """Señal interna para abortar el atomic en dry-run sin persistir."""
    pass
