"""Corrección de metas Cultura 2780 (cuatrienio real) — 2026-06-09.

Datos confirmados por el Área de Cultura:
  M1 Capacitar 4000 personas        — estrategia EXPLORARTE
  M2 Beneficiar 60 organizaciones   — estrategia MÁS CULTURA LOCAL  (era 15)
  M3 Otorgar 140 estímulos          — estrategia MÁS CULTURA LOCAL  (era 38)
  M4 Realizar 60 eventos (NUEVA)    — estrategia OPERADOR LOGÍSTICO

Aditivo/idempotente. Corrige meta_magnitud + estampa la ESTRATEGIA (la "meta
grande" a la que le pega) en indicador.descripcion. Crea M4 (meta+KPI+actividad).
NO toca avances.

Ejecutar:  docker exec innova_k python scripts/fix_metas_cultura_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import transaction
from apps.presupuesto.models.indicadores import (
    Indicador, MetaBD, MetaProyectoBD, ActividadIndicador,
)
from apps.presupuesto.models.core import ActividadPlan


def main():
    with transaction.atomic():
        # ── Corregir cantidades + estrategia de M1/M2/M3 ─────────────
        ajustes = [
            ("Capacitar",  4000, "EXPLORARTE"),
            ("Beneficiar", 60,   "MÁS CULTURA LOCAL"),
            ("Otorgar",    140,  "MÁS CULTURA LOCAL"),
        ]
        for clave, cant, estrategia in ajustes:
            for kpi in Indicador.objects.filter(
                meta_proyecto__proyecto_id=1, nombre__icontains=clave, activo=True
            ):
                kpi.meta_magnitud = cant
                kpi.descripcion = f"Estrategia: {estrategia}"
                kpi.save(update_fields=["meta_magnitud", "descripcion"])
                print(f"  KPI {kpi.id} '{kpi.nombre[:34]}' → {cant} | {estrategia}")

        # ── Crear Meta 4 (60 eventos, Operador Logístico) ────────────
        nombre_m4 = ("Realizar eventos de promoción, circulación y apropiación "
                     "de actividades artísticas, culturales y patrimoniales")
        meta, _ = MetaBD.objects.get_or_create(nombre=nombre_m4)
        mp, _ = MetaProyectoBD.objects.get_or_create(meta_id=meta.codigo, proyecto_id=1)
        kpi4, creado = Indicador.objects.get_or_create(
            meta_proyecto_id=mp.id, nombre=nombre_m4,
            defaults=dict(unidad_medida="eventos", meta_magnitud=60,
                          tipo_agregacion="SUMA", activo=True,
                          descripcion="Estrategia: OPERADOR LOGÍSTICO"),
        )
        ap, _ = ActividadPlan.objects.get_or_create(
            proyecto_id=1, descripcion="Realización de eventos culturales (promoción y circulación)")
        ActividadIndicador.objects.get_or_create(
            actividad_plan_id=ap.id, indicador_id=kpi4.id, defaults={"activo": True})
        print(f"  Meta 4 → KPI {kpi4.id} 60 eventos ({'creada' if creado else 'existía'}) | OPERADOR LOGÍSTICO")
        print("COMMIT OK")


if __name__ == "__main__":
    main()
