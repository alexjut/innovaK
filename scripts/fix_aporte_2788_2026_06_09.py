"""Niveles general vs aporte del proyecto 2788 (vigencia) — 2026-06-09.

Aclaración del Área de Cultura:
  META GENERAL (cuatrienio) del 2788 KENNEDY IMPULSO CREATIVO:
    - Financiar 140 proyectos del sector cultural y creativo.
  APORTE de ESTA VIGENCIA (2026), lo que dice DESCRIPCIÓN META:
    - Financiar 35 proyectos  (presupuesto $1.889.377.000).
  Las vigencias siguientes financian el resto hasta los 140.

  El 2788 reporta a la Meta 1 EXPLORARTE (Capacitar 4000) solo como RÓTULO
  SIPSE. NO se mezcla con el 2780 (otro contrato): cada proyecto vive en su
  360° aparte, sin sumar plata ni avances entre contratos.

Modelo (igual que fix_aporte_2780): `metas` (catálogo) = META GENERAL (140) ;
Indicador.meta_magnitud = APORTE de la vigencia (35). Aditivo, no toca avances,
no toca el 2780.

Ejecutar:  docker exec innova_k python scripts/fix_aporte_2788_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import transaction
from apps.presupuesto.models.indicadores import Indicador, MetaBD

META_GENERAL = "Financiar 140 proyectos del sector cultural y creativo (EXPLORARTE)"
APORTE_VIGENCIA = 35
PRESUPUESTO = "$1.889.377.000"


def main():
    with transaction.atomic():
        for kpi in Indicador.objects.filter(
            meta_proyecto__proyecto_id=2788, nombre__icontains="Financiar", activo=True
        ).select_related("meta_proyecto"):
            # KPI = aporte de la vigencia (35 de los 140)
            kpi.meta_magnitud = APORTE_VIGENCIA
            kpi.unidad_medida = "proyectos"
            kpi.descripcion = (f"Estrategia: EXPLORARTE (rótulo SIPSE) · "
                               f"Aporte vigencia 2026 · Financiar 35 de 140 proyectos · "
                               f"Presupuesto {PRESUPUESTO}")
            kpi.save(update_fields=["meta_magnitud", "unidad_medida", "descripcion"])
            # metas (catálogo) = META GENERAL (140, cuatrienio)
            meta = MetaBD.objects.filter(codigo=kpi.meta_proyecto.meta_id).first()
            if meta:
                meta.nombre = META_GENERAL
                meta.save(update_fields=["nombre"])
            print(f"  KPI {kpi.id}: aporte 2788 = 35 proyectos | "
                  f"meta general = '{META_GENERAL[:50]}…' | {PRESUPUESTO}")
        print("COMMIT OK — 2788 con general(140)/aporte(35), 2780 intacto.")


if __name__ == "__main__":
    main()
