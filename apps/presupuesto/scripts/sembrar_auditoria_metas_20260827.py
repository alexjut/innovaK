"""Siembra la auditoría que le faltó a 8 enganches meta ↔ SEGPLAN.

QUÉ PASÓ. El 2026-08-27, `sdp_mapear_codigo_meta --apply` escribió el
`codigo_meta` de 8 metas sin exigir firma ni dejar rastro: la guarda `--usuario`
y el `registrar_cambio` se agregaron DESPUÉS, en el mismo día, a raíz de eso.
Los valores están verificados uno por uno (contención 1.00 con margen sobre la
segunda candidata), pero quedaron sin origen registrado, y un enganche con la
fuente oficial que no se puede rastrear vale poco: si mañana una cifra oficial
no cuadra, nadie puede saber quién ató esa meta ni con qué criterio.

QUÉ SIEMBRA. Una fila de auditoría por meta, diciendo con todas las letras que
es retroactiva y por qué. NO se inventa la hora: el `created_at` es el de la
siembra, y la observación aclara que el cambio ocurrió antes ese mismo día.

QUÉ **NO** TOCA. Las 11 metas que ya tenían `codigo_meta` antes del 2026-08-27.
De esas no sé quién ni cómo las enganchó —vienen de una corrida anterior del
algoritmo viejo—, y escribirles una auditoría sería afirmar algo que no me
consta. Se quedan sin rastro, que es la verdad.

Idempotente: si la meta ya tiene su fila de auditoría, no crea otra.

Uso:
    docker exec innova_k python apps/presupuesto/scripts/sembrar_auditoria_metas_20260827.py --usuario alexjut
"""
import argparse
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection  # noqa: E402

from apps.presupuesto.models.auditoria import AuditoriaDato  # noqa: E402
from apps.presupuesto.services.auditoria import registrar_cambio  # noqa: E402

# Las 8, con el código oficial que se les escribió. Se listan a mano y no se
# deducen de la base: la lista ES el alcance del arreglo, y una consulta que
# "encuentre las que faltan" barrería también las 11 anteriores.
ESCRITAS_SIN_AUDITORIA = [7, 100023, 100024, 100025, 100026, 100027, 100028, 100029]

OBSERVACION = (
    "Auditoría RETROACTIVA, sembrada el mismo 2026-08-27. El enganche con "
    "SEGPLAN se escribió horas antes por `sdp_mapear_codigo_meta --apply` "
    "cuando el comando todavía no exigía firma ni registraba nada. El valor "
    "está verificado (el nombre interno está contenido entero en el oficial, "
    "con margen sobre la segunda candidata del mismo proyecto), pero su origen "
    "no había quedado registrado.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuario", required=True,
                    help="Username que firma la siembra.")
    ap.add_argument("--apply", action="store_true",
                    help="Escribe. Sin esto solo muestra qué haría.")
    opts = ap.parse_args()

    usuario = get_user_model().objects.filter(username=opts.usuario).first()
    if usuario is None:
        sys.exit(f"No existe el usuario «{opts.usuario}».")

    ya = set(AuditoriaDato.objects
             .filter(entidad="meta", campo="codigo_meta",
                     entidad_id__in=ESCRITAS_SIN_AUDITORIA)
             .values_list("entidad_id", flat=True))

    with connection.cursor() as c:
        c.execute("SELECT codigo, codigo_meta FROM metas WHERE codigo = ANY(%s)",
                  [ESCRITAS_SIN_AUDITORIA])
        valores = dict(c.fetchall())

    pendientes = [(m, valores.get(m)) for m in ESCRITAS_SIN_AUDITORIA
                  if m not in ya and valores.get(m)]

    print(f"metas del alcance: {len(ESCRITAS_SIN_AUDITORIA)} · "
          f"ya auditadas: {len(ya)} · a sembrar: {len(pendientes)}")
    for meta, oficial in pendientes:
        print(f"  meta {meta} → SEGPLAN {oficial}")

    if not opts.apply:
        print("\n(seco: nada se escribió. Agrega --apply para sembrar.)")
        return

    n = 0
    for meta, oficial in pendientes:
        fila = registrar_cambio(
            usuario=usuario, entidad="meta", entidad_id=meta,
            campo="codigo_meta", valor_anterior=None, valor_nuevo=str(oficial),
            fuente=AuditoriaDato.SEGPLAN, observacion=OBSERVACION)
        if fila is None:
            # `registrar_cambio` NUNCA lanza —a propósito, para no perder el
            # dato si la auditoría falla—, así que un error acá se traga en
            # silencio y el script reportaría éxito sin haber escrito nada.
            # Justo lo que pasó la primera vez, con una constante que no
            # existía. Se cuenta y se dice.
            print(f"  ⚠ meta {meta}: la auditoría NO se creó (revisar el log)")
            continue
        n += 1
    print(f"\nOK: {n} de {len(pendientes)} filas de auditoría sembradas, "
          f"firmadas por {opts.usuario}.")


if __name__ == "__main__":
    main()
