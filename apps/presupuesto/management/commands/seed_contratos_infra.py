"""Ingesta idempotente de los contratos de infraestructura + sus vías y
parques de obra (subgrupo Infraestructura).

Fuente de verdad: apps/presupuesto/seeds/contratos_infraestructura.json

Hace upsert por clave natural (no duplica si se corre 2 veces):
  - Proyecto:      codigo (2574, 2790) + cadena stub (Meta→MetaProyecto→KPI).
  - Contrato:      (contrato_tipo, contrato_numero, contrato_vigencia).
  - ContratoProyecto: (contrato, proyecto).
  - TramoVialContrato: (contrato, civ)  — geom se resuelve aparte (PR-2).
  - IntervencionParque: (parque, contrato), reusando la tabla `parque`.

La geometría de las vías NO se descarga aquí (queda geo_status='PENDIENTE');
eso lo hace `resolver_geometria_tramos` en PR-2.

    python manage.py seed_contratos_infra
"""
import json
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.georeferenciacion.models.models_catalogos import Parque
from apps.georeferenciacion.utils import crear_con_fallback_id
from apps.presupuesto.models import (
    Contrato, ContratoProyecto, Proyecto, TramoVialContrato, IntervencionParque,
)
from apps.presupuesto.models.indicadores import MetaBD, MetaProyectoBD, Indicador

SUBGRUPO_INFRAESTRUCTURA = 37  # dependencia Inversión Local (verificado en BD)

SEED = os.path.join(os.path.dirname(__file__), "..", "..", "seeds",
                    "contratos_infraestructura.json")

# Meta/KPI stub por proyecto (decisión de Alex: stub, ajustar magnitudes luego).
STUB = {
    "2574": {"meta": "Intervención de malla vial local", "kpi": "Tramos viales intervenidos",
             "unidad": "Tramo", "magnitud": 30},
    "2790": {"meta": "Mantenimiento de parques de proximidad", "kpi": "Parques intervenidos",
             "unidad": "Parque", "magnitud": 14},
}


class Command(BaseCommand):
    help = "Ingesta idempotente de contratos de infraestructura (vías + parques)."

    @transaction.atomic
    def handle(self, *args, **options):
        with open(SEED, encoding="utf-8") as fh:
            data = json.load(fh)

        proyectos = self._upsert_proyectos(data["contratos"])
        contratos = self._upsert_contratos(data["contratos"], proyectos)
        self._upsert_tramos(data["tramos_viales"], contratos)
        self._upsert_parques(data["parques"], contratos)

        self.stdout.write(self.style.SUCCESS("seed_contratos_infra: OK."))

    # ── Proyectos + cadena stub ──────────────────────────────────────────
    def _upsert_proyectos(self, contratos):
        out = {}
        codigos = {c["proyecto_codigo"]: c["proyecto_nombre"] for c in contratos}
        for cod, nombre in codigos.items():
            proy, creado = Proyecto.objects.get_or_create(
                codigo=cod,
                defaults={"nombre": nombre, "subgrupo_id": SUBGRUPO_INFRAESTRUCTURA},
            )
            out[cod] = proy
            self.stdout.write(f"  Proyecto {cod}: {'creado' if creado else 'existe'} (id={proy.id})")
            self._stub_cadena(proy, cod)
        return out

    def _stub_cadena(self, proy, cod):
        spec = STUB.get(cod)
        if not spec:
            return
        meta, _ = MetaBD.objects.get_or_create(nombre=spec["meta"])
        mp, _ = MetaProyectoBD.objects.get_or_create(meta=meta, proyecto=proy)
        Indicador.objects.get_or_create(
            meta_proyecto=mp, nombre=spec["kpi"],
            defaults={"unidad_medida": spec["unidad"],
                      "meta_magnitud": Decimal(str(spec["magnitud"])),
                      "tipo_agregacion": "SUMA"},
        )

    # ── Contratos ────────────────────────────────────────────────────────
    def _upsert_contratos(self, filas, proyectos):
        out = {}
        for c in filas:
            tipo, numero, vigencia = c["contrato"].split("-")
            numero, vigencia = int(numero), int(vigencia)
            campos = {
                "objeto": c.get("objeto"),
                "valor": Decimal(str(c["valor"])) if c.get("valor") is not None else None,
                "fecha_inicio": c.get("fecha_inicio") or None,
                "fecha_fin": c.get("fecha_terminacion") or None,
                "categoria": c.get("categoria"),
                "proyecto_codigo": c.get("proyecto_codigo"),
                "proyecto_nombre": c.get("proyecto_nombre"),
                "ejecucion": c.get("ejecucion"),
                "interventoria_contrato": c.get("interventoria_contrato"),
                "interventoria_valor": (Decimal(str(c["interventoria_valor"]))
                                        if c.get("interventoria_valor") is not None else None),
            }
            obj = (Contrato.objects
                   .filter(contrato_tipo=tipo, contrato_numero=numero,
                           contrato_vigencia=vigencia).first())
            if obj:
                for k, v in campos.items():
                    setattr(obj, k, v)
                obj.save()
                estado = "actualizado"
            else:
                obj = crear_con_fallback_id(
                    Contrato, contrato_tipo=tipo, contrato_numero=numero,
                    contrato_vigencia=vigencia, **campos)
                estado = "creado"
            out[c["contrato"]] = obj
            # Vínculo al proyecto (cadena Proyecto→Contrato).
            proy = proyectos.get(c["proyecto_codigo"])
            if proy:
                ContratoProyecto.objects.get_or_create(contrato=obj, proyecto=proy)
            self.stdout.write(f"  Contrato {c['contrato']}: {estado} (id={obj.id})")
        return out

    # ── Tramos viales (geom pendiente) ───────────────────────────────────
    def _upsert_tramos(self, filas, contratos):
        n = 0
        for t in filas:
            contrato = contratos.get(t["contrato"])
            if not contrato:
                continue
            TramoVialContrato.objects.update_or_create(
                contrato=contrato, civ=t["civ"],
                defaults={
                    "pk_id": t.get("pk_id"),
                    "eje_vial": t.get("eje_vial"),
                    "desde": t.get("desde"),
                    "hasta": t.get("hasta"),
                    "valor_intervencion": (Decimal(str(t["valor_intervencion"]))
                                           if t.get("valor_intervencion") is not None else None),
                    "pct_avance": t.get("pct_avance", 0),
                    # geom/geo_status NO se tocan si ya estaban resueltos (PR-2).
                },
            )
            n += 1
        self.stdout.write(f"  Tramos viales upsert: {n}")

    # ── Parques (reusa tabla parque) + intervención ──────────────────────
    def _upsert_parques(self, filas, contratos):
        n, faltan = 0, []
        for p in filas:
            contrato = contratos.get(p["contrato"])
            if not contrato:
                continue
            parque = Parque.objects.filter(id_parque=p["codigo_parque"]).first()
            if not parque:
                faltan.append(p["codigo_parque"])
                continue
            IntervencionParque.objects.update_or_create(
                parque=parque, contrato=contrato,
                defaults={"pct_avance": p.get("pct_avance", 0),
                          "direccion": p.get("direccion")},
            )
            n += 1
        self.stdout.write(f"  Intervenciones de parque upsert: {n}")
        if faltan:
            self.stdout.write(self.style.WARNING(
                f"  Parques NO encontrados en tabla `parque` (revisión): {faltan}"))
