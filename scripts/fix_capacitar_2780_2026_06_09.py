"""Niveles general vs aporte de Capacitar (2780 M1) — 2026-06-09.

Aclaración del Área de Cultura:
  META GENERAL (cuatrienio, EXPLORARTE):
    - Capacitar 4000 personas en campos artísticos, interculturales,
      culturales y/o patrimoniales.
  APORTE de ESTA VIGENCIA (2026) del contrato 2780:
    - Capacitar 1000 personas.
  El resto (hasta 4000) lo aportan otras vigencias / otros proyectos.

Modelo (igual que Beneficiar/Otorgar): `metas` (catálogo) = META GENERAL (4000) ;
Indicador.meta_magnitud = APORTE de la vigencia (1000). Aditivo, no toca avances.

Ejecutar:  docker exec innova_k python scripts/fix_capacitar_2780_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import transaction
from apps.presupuesto.models.indicadores import Indicador, MetaBD

META_GENERAL = ("Capacitar 4000 personas en los campos artísticos, interculturales, "
                "culturales y/o patrimoniales (EXPLORARTE)")
APORTE_VIGENCIA = 1000


def main():
    with transaction.atomic():
        for kpi in Indicador.objects.filter(
            meta_proyecto__proyecto_id=1, nombre__icontains="Capacitar", activo=True
        ).select_related("meta_proyecto"):
            # KPI = aporte de la vigencia (1000 de los 4000)
            kpi.meta_magnitud = APORTE_VIGENCIA
            kpi.unidad_medida = "personas"
            kpi.descripcion = ("Estrategia: EXPLORARTE · Aporte vigencia 2026 · "
                               "Capacitar 1000 de 4000 personas")
            kpi.save(update_fields=["meta_magnitud", "unidad_medida", "descripcion"])
            # metas (catálogo) = META GENERAL (4000, cuatrienio)
            meta = MetaBD.objects.filter(codigo=kpi.meta_proyecto.meta_id).first()
            if meta:
                meta.nombre = META_GENERAL
                meta.save(update_fields=["nombre"])
            print(f"  KPI {kpi.id}: aporte 2780 = 1000 personas | "
                  f"meta general = '{META_GENERAL[:50]}…'")
        print("COMMIT OK — Capacitar 2780 con general(4000)/aporte(1000).")


if __name__ == "__main__":
    main()
