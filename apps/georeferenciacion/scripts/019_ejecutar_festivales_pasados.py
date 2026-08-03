"""Marca como ejecutados los festivales publicados cuya fecha ya pasó.

Correr DESPUÉS del 018: sin actos no hay nada que sumar.

El estado es el disparador del avance (`sincronizar_festival`): al pasar a
`ejecutado` cada acto suma +1 al KPI de su actividad del plan, con el marcador
`festival=<id>` en las observaciones. Es idempotente —volver a correrlo no
duplica— y **reversible**: devolver el festival a `planeado` borra sus avances.

Solo toca festivales publicados con `fecha_fin` (o `fecha_inicio`) anterior a
hoy. Uno que todavía no ocurre no se marca ejecutado por más publicado que esté.
"""
from datetime import date

from django.db import transaction
from apps.festivales.models import Festival
from apps.festivales.services.avance import sincronizar_festival

hoy = date.today()
total_creados = 0

for f in Festival.objects.filter(publicado=True).order_by("id"):
    fin = f.fecha_fin or f.fecha_inicio
    if fin is None:
        print(f"id={f.id} {f.nombre[:34]:<34} sin fecha — se salta")
        continue
    if fin >= hoy:
        print(f"id={f.id} {f.nombre[:34]:<34} termina {fin} (aún no pasa) — se salta")
        continue
    if f.estado != Festival.PLANEADO:
        print(f"id={f.id} {f.nombre[:34]:<34} ya estaba en '{f.estado}'")
        continue
    if not f.eventos.exists():
        print(f"id={f.id} {f.nombre[:34]:<34} SIN actos — correr antes el 018")
        continue

    with transaction.atomic():
        f.estado = Festival.EJECUTADO
        f.save(update_fields=["estado"])
        r = sincronizar_festival(f)
    total_creados += r["creados"]
    print(f"id={f.id} {f.nombre[:34]:<34} -> ejecutado | avances creados: {r['creados']}")

print("=" * 84)
print(f"avances creados en total: {total_creados}")

# Foto del KPI al que aportan, para verificar de una vez.
from apps.festivales.services.avance import kpi_de_festivales
kpi = kpi_de_festivales(2026)
if kpi:
    print(f"KPI {kpi['indicador_id']} — {kpi['nombre'][:52]}")
    print(f"   meta={kpi['meta']} avance_total={kpi['avance_total']} "
          f"(de festivales: {kpi['avance_festivales']})")
else:
    print("Sin KPI conectado todavía.")
