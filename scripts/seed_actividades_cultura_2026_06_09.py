"""Seed — actividades de Cultura: actividad_plan + vínculo KPI + EVENTO — 2026-06-09.

Aditivo, idempotente. Por cada meta de Cultura (2780/2788) crea:
  1. ActividadPlan (la actividad del plan).
  2. ActividadIndicador (la liga al KPI → los avances suman).
  3. Evento del tipo correspondiente, bajo subgrupo Cultura, ligado a la
     actividad_plan + KPI, ABIERTO (fecha_fin futura) → así sale en el hub de
     Actividades con su QR/Formulario/Registros.

Tipos usados (catálogo existente, sin crear parecidos):
  - Capacitar 4000 personas  → CURSO  (Escuela de Formación Explorarte)
  - Beneficiar 15 orgs       → CULTURA_ORG
  - Otorgar 38 estímulos     → ESTIMULO_CULTURAL
  - Financiar 35 proyectos   → PROYECTO_CULTURAL

Ejecutar:  docker exec innova_k python scripts/seed_actividades_cultura_2026_06_09.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import transaction
from apps.presupuesto.models.core import ActividadPlan
from apps.presupuesto.models.indicadores import Indicador, ActividadIndicador
from apps.login.models.evento import Evento

SUBGRUPO_CULTURA = 1
FECHA_FIN = date(2026, 12, 31)

# (palabra clave KPI, descripción actividad, tipo_evento, nombre del evento)
MAPEO = [
    ("Capacitar",  "Escuela de Formación Artística Explorarte",
     "CURSO", "Escuela de Formación Artística Explorarte 2026"),
    ("Beneficiar", "Apoyo y fortalecimiento de organizaciones culturales",
     "CULTURA_ORG", "Beneficio a organizaciones culturales 2026"),
    ("Otorgar",    "Otorgamiento de estímulos al sector artístico y cultural",
     "ESTIMULO_CULTURAL", "Estímulos al sector artístico y cultural 2026"),
    ("Financiar",  "Financiación de proyectos del sector cultural y creativo",
     "PROYECTO_CULTURAL", "Proyectos culturales financiados 2026"),
]


def main():
    with transaction.atomic():
        kpis = list(
            Indicador.objects.filter(meta_proyecto__proyecto_id__in=[1, 2788], activo=True)
            .select_related("meta_proyecto")
        )
        print(f"KPIs de Cultura: {len(kpis)}")
        for kpi in kpis:
            m = next((x for x in MAPEO if x[0].lower() in (kpi.nombre or "").lower()), None)
            if not m:
                print(f"  [SKIP] KPI {kpi.id} '{kpi.nombre[:35]}'")
                continue
            _, desc, tipo, nombre_ev = m
            proy_id = kpi.meta_proyecto.proyecto_id

            ap, c_ap = ActividadPlan.objects.get_or_create(proyecto_id=proy_id, descripcion=desc)
            ai, c_ai = ActividadIndicador.objects.get_or_create(
                actividad_plan_id=ap.id, indicador_id=kpi.id, defaults={"activo": True})
            ev, c_ev = Evento.objects.get_or_create(
                nombre=nombre_ev, tipo_evento_id=tipo,
                defaults=dict(subgrupo_id=SUBGRUPO_CULTURA, actividad_plan_id=ap.id,
                              indicador_id=kpi.id, activo=True,
                              fecha_inicio=date.today(), fecha_fin=FECHA_FIN),
            )
            print(f"  proy={proy_id} KPI={kpi.id} → act '{desc[:32]}' + evento [{tipo}] "
                  f"id={ev.id} '{nombre_ev[:30]}' "
                  f"(ap:{'+' if c_ap else '='} vinc:{'+' if c_ai else '='} ev:{'+' if c_ev else '='})")
        print("COMMIT OK")


if __name__ == "__main__":
    main()
