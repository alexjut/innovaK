"""Crea los actos de los festivales publicados y los engancha a la cadena.

Por qué hace falta: el avance a la meta lo suma **cada acto ejecutado**, no el
festival (`apps/festivales/services/avance.py`). Los 9 festivales de 2026 no
tienen ni un acto, así que marcarlos ejecutados dejaría el KPI en 0 igual. Esto
crea el eslabón que falta:

    Evento(acto) → actividad_plan 113 → KPI 15 → Meta 4 → proyecto 2780

Criterios, para no inventar nada:

- **Un acto por día registrado.** Si el festival no tiene días, se crea UN acto
  con su `fecha_inicio`. No se parten festivales en días que nadie registró.
- **El punto es el del festival**, que ya tiene latitud/longitud propias. No se
  usa la sede de la Alcaldía: sería ubicarlos donde no fueron, justo lo que se
  corrigió hoy en el mapa.
- **Idempotente:** un festival que ya tenga actos se salta entero.
- **No cambia el estado.** Que un festival pase a `ejecutado` es decisión del
  área, y es lo que dispara el avance (ver 019).
"""
from decimal import Decimal

from django.db import transaction
from apps.festivales.models import Festival
from apps.login.models import Evento
from apps.georeferenciacion.models.models_localizacion import (
    GeoReferenciacion, LugarIncidencia,
)
from apps.georeferenciacion.utils import crear_con_fallback_id, get_lugar_generico

ACTIVIDAD_PLAN = 113          # "Realización de eventos culturales" → KPI 15
TIPO = "FESTIVAL"


def _subgrupo_y_dependencia():
    """Ids de Cultura / Inversión Local, buscados por nombre y no quemados."""
    from apps.login.models import Dependencia, Subgrupo
    sub = Subgrupo.objects.filter(nombre__icontains="cultura").order_by("id").first()
    dep = (Dependencia.objects.filter(nombre__icontains="inversi").order_by("id").first()
           or Dependencia.objects.order_by("id").first())
    return (sub.id if sub else None), (dep.id if dep else None)


def _lugar_del_festival(f):
    """LugarIncidencia con el punto propio del festival. `None` si no tiene."""
    if f.latitud is None or f.longitud is None:
        return None
    geo = crear_con_fallback_id(
        GeoReferenciacion,
        latitud=Decimal(str(f.latitud)),
        longitud=Decimal(str(f.longitud)),
        direccion_texto=(f.lugar_texto or f.nombre or "")[:200],
        fuente="manual", precision="manual_click",
        lugar=get_lugar_generico(),
    )
    return crear_con_fallback_id(LugarIncidencia, geo_referenciacion=geo)


sub_id, dep_id = _subgrupo_y_dependencia()
print(f"subgrupo Cultura={sub_id}  dependencia Inversión Local={dep_id}")
print("=" * 84)

creados = 0
for f in Festival.objects.filter(publicado=True).order_by("id"):
    ya = f.eventos.count()
    if ya:
        print(f"id={f.id} {f.nombre[:34]:<34} ya tiene {ya} acto(s) — se salta")
        continue

    dias = list(f.dias.all().order_by("fecha"))
    fechas = [d.fecha for d in dias] or ([f.fecha_inicio] if f.fecha_inicio else [])
    if not fechas:
        print(f"id={f.id} {f.nombre[:34]:<34} SIN fecha ni dias — no se puede crear el acto")
        continue

    with transaction.atomic():
        li = _lugar_del_festival(f)
        for i, fecha in enumerate(fechas, start=1):
            nombre = f.nombre if len(fechas) == 1 else f"{f.nombre} — día {i}"
            ev = crear_con_fallback_id(
                Evento,
                nombre=nombre[:200],
                descripcion=f"Acto del festival «{f.nombre}».",
                tipo_evento_id=TIPO,
                fecha_inicio=fecha,
                fecha_fin=fecha,
                dependencia_id=dep_id,
                subgrupo_id=sub_id,
                actividad_plan_id=ACTIVIDAD_PLAN,
                festival_id=f.id,
                lugar_incidencia_id=(li.id if li else None),
            )
            creados += 1
            print(f"id={f.id} {f.nombre[:30]:<30} -> acto {ev.id} ({fecha}) "
                  f"lugar={'propio' if li else 'sin punto'}")

print("=" * 84)
print(f"actos creados: {creados}")
print("Los festivales siguen en 'planeado': el avance al KPI se dispara cuando")
print("el area los marque ejecutados (script 019 o el boton del detalle).")
