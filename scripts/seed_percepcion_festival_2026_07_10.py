"""Seed — tipo_evento PERCEPCION_FESTIVAL (encuesta ciudadana) — 2026-07-10.

Crea el ÚNICO tipo de evento que usan todos los festivales (presentes y
futuros) para la encuesta de percepción de impacto. El cuestionario vive
como schema data-driven en `apps.login.services.captura_schema`
(`PERCEPCION_FESTIVAL`); este seed solo registra la fila de catálogo
`tipo_evento` para que se puedan crear eventos de este tipo y su QR se
enrute solo a `/app/p/captura/<evento_id>`.

Claves de diseño:
- `requiere_actividad_plan = FALSE`: la encuesta es un instrumento de
  percepción con MUCHAS respuestas por festival; NO es captura de
  beneficiarios. Al no colgar de una actividad-plan, validar una respuesta
  no crea AvanceIndicador (ver _sync_kpi en captura_organizador: early-return
  si el evento no tiene actividad_plan_id). El festival como evento cultural
  cuenta aparte hacia "Realizar eventos"; cada encuesta no debe sumar +1.
- `permite_qr = TRUE`: el ciudadano lo llena por QR.

Idempotente: si el tipo ya existe, no lo duplica ni lo pisa.
Aditivo (una fila de catálogo). Sin DDL.

Ejecutar:  docker exec innova_k python scripts/seed_percepcion_festival_2026_07_10.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection, transaction

CODIGO = "PERCEPCION_FESTIVAL"
NOMBRE = "Percepción de festival"
DESCRIPCION = (
    "Encuesta ciudadana de percepción del impacto cultural, social y de "
    "identidad de los festivales de Kennedy (formulario general para todos "
    "los festivales, se llena por QR)."
)
ICONO = "fa-masks-theater"
COLOR = "#7E22CE"


def main():
    cur = connection.cursor()
    with transaction.atomic():
        cur.execute("SELECT codigo FROM tipo_evento WHERE codigo=%s", [CODIGO])
        if cur.fetchone():
            print(f"tipo_evento {CODIGO} ya existe — no se toca.")
            return
        cur.execute(
            """INSERT INTO tipo_evento
                 (codigo, nombre, descripcion, activo, icono, color, orden,
                  permite_inscripcion, permite_caracterizacion, permite_qr,
                  requiere_actividad_plan)
               VALUES (%s, %s, %s, true, %s, %s, 55,
                       false, false, true, false)""",
            [CODIGO, NOMBRE, DESCRIPCION, ICONO, COLOR],
        )
        print(f"tipo_evento {CODIGO} creado (requiere_actividad_plan=false).")
        print("COMMIT OK.")


if __name__ == "__main__":
    main()
