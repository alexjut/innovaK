"""Crea el evento de caracterización del subgrupo Paz (Proyecto 2106).

Idempotente: si ya existe un evento CARACTERIZACION/paz en el subgrupo 41, no
crea otro. Correr dentro del contenedor:
    docker exec innova_k python /app/apps/caracterizacion/scripts/crear_evento_paz.py

Esto hace que Paz aparezca en /app/actividades (el subgrupo pasa a tener 1 evento)
y habilita el formulario público /app/p/caracterizacion/<id>.
"""
import os
import sys

BASE = "/app"
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from datetime import date, timedelta  # noqa: E402

from apps.login.models.evento import Evento  # noqa: E402

SUBGRUPO_PAZ = 41
DEP_INVERSION_LOCAL = 3

ev = Evento.objects.filter(
    tipo_evento_id="CARACTERIZACION",
    sector_caracterizacion="paz",
    subgrupo_id=SUBGRUPO_PAZ,
).first()

if ev:
    print("Ya existía el evento Paz. id:", ev.id)
else:
    ev = Evento.objects.create(
        nombre="Caracterización Paz, Memoria y Reconciliación (Proyecto 2106)",
        tipo_evento_id="CARACTERIZACION",
        sector_caracterizacion="paz",
        subgrupo_id=SUBGRUPO_PAZ,
        dependencia_id=DEP_INVERSION_LOCAL,
        activo=True,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=365),
    )
    print("Evento Paz CREADO. id:", ev.id)

print("Formulario público (QR): /app/p/caracterizacion/%s" % ev.id)
print("Panel organizador: /app/caracterizacion")
