"""Corrige niveles meta general vs aporte del proyecto 2780 — 2026-06-09.

Aclaración del Área de Cultura:
  META GENERAL (MÁS CULTURA LOCAL):
    - Beneficiar 60 organizaciones (con elementos entregados)
    - Otorgar 140 estímulos
  El proyecto 2780 SOLO APORTA (DESCRIPCIÓN META):
    - 15 organizaciones  (presupuesto $680.176.000)
    - 38 estímulos       (presupuesto $1.133.626.000)
  Otros proyectos llenan el resto de la meta general.

Modelo: `metas` (catálogo) = META GENERAL (60/140) ; Indicador.meta_magnitud =
APORTE del 2780 (15/38). El proyecto 360 muestra meta_nombre (general) + KPI
(aporte). Aditivo, no toca avances.

Ejecutar:  docker exec innova_k python scripts/fix_aporte_2780_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import transaction
from apps.presupuesto.models.indicadores import Indicador, MetaBD

# clave KPI → (aporte 2780, nombre META GENERAL, presupuesto meta)
DATOS = {
    "Beneficiar": (15,  "Beneficiar 60 organizaciones artísticas, culturales y patrimoniales con elementos entregados (MÁS CULTURA LOCAL)", "$680.176.000"),
    "Otorgar":    (38,  "Otorgar 140 estímulos de apoyo al sector artístico y cultural (MÁS CULTURA LOCAL)", "$1.133.626.000"),
}


def main():
    with transaction.atomic():
        for clave, (aporte, meta_general, presupuesto) in DATOS.items():
            for kpi in Indicador.objects.filter(
                meta_proyecto__proyecto_id=1, nombre__icontains=clave, activo=True
            ).select_related("meta_proyecto"):
                # KPI = aporte del proyecto
                kpi.meta_magnitud = aporte
                kpi.descripcion = (f"Estrategia: MÁS CULTURA LOCAL · "
                                   f"Aporte del 2780 a la meta general · Presupuesto {presupuesto}")
                kpi.save(update_fields=["meta_magnitud", "descripcion"])
                # metas (catálogo) = META GENERAL
                meta = MetaBD.objects.filter(codigo=kpi.meta_proyecto.meta_id).first()
                if meta:
                    meta.nombre = meta_general
                    meta.save(update_fields=["nombre"])
                print(f"  KPI {kpi.id}: aporte 2780 = {aporte} | meta general = '{meta_general[:50]}…'")
        print("COMMIT OK")


if __name__ == "__main__":
    main()
