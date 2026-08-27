"""Le da a Paz su proyecto y le muda la meta que estaba colgada de una fila basura.

QUÉ ESTABA MAL. La meta 10 («camino seguro las mujeres») colgaba del proyecto
2807, cuyo `codigo` Y `nombre` son ambos «000007895»: alguien creó un proyecto
escribiendo un número en los dos campos. De ahí colgaba también la actividad
del plan 107, «mujeres caminando ver 1».

Por eso esa meta nunca cruzó con SEGPLAN: no era un problema de emparejamiento
de textos, era que estaba en el proyecto equivocado. Alex confirmó el
2026-08-27 que pertenece al 2818, que en SDP es «KENNEDY CAMINOS DE
RECONCILIACIÓN» — el proyecto de Paz.

Y el subgrupo 41, «Paz, Memoria y Reconciliación», tenía CERO proyectos. No es
que le faltara uno: es que el suyo estaba mal escrito en otro lado, y por eso
el área no aparecía en ningún tablero que agrupe por proyecto.

QUÉ HACE, en una transacción:
  1. Crea el proyecto 2818 con el nombre oficial de SDP, en el subgrupo 41.
  2. Le muda la fila de `meta_proyecto` de la meta 10.
  3. Le muda la actividad del plan 107.

QUÉ **NO** HACE, a propósito:
  · No borra el proyecto 2807. Queda vacío y a la vista, que es mejor que
    desaparecerlo: si mañana alguien busca por qué existía, lo encuentra.
    Borrarlo es una decisión aparte y de Alex.
  · No escribe `metas.codigo_meta`. El proyecto 2818 tiene TRES metas oficiales
    (28181 acciones de construcción de paz, 28182 fortalecimiento de la
    población víctima, 28183 procesos pedagógicos) y «camino seguro las
    mujeres» no calza con ninguna por texto. Eso lo elige una persona, con
    `sdp_mapear_codigo_meta --manual 10:XXXXX`.

DETALLES QUE COSTARON UN RATO:
  · `proyecto.id` es IDENTITY **GENERATED ALWAYS**. No se le pasa valor, ni
    siquiera uno sacado de su propia secuencia: Postgres lo rechaza igual. Y
    `information_schema.columns.column_default` sale NULL para estas columnas,
    así que mirar ahí hace creer que no tienen nada — hay que mirar
    `is_identity`.
  · `proyecto.nombre_ci` es GENERATED ALWAYS: insertarla revienta con «cannot
    insert a non-DEFAULT value into a generated column».

Uso:
    docker exec innova_k python apps/presupuesto/scripts/mudar_meta10_a_paz_20260827.py
    docker exec innova_k python apps/presupuesto/scripts/mudar_meta10_a_paz_20260827.py --apply --usuario alexjut
"""
import argparse
import os
import sys
from pathlib import Path

import django

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection, transaction  # noqa: E402

from apps.presupuesto.models.auditoria import AuditoriaDato  # noqa: E402
from apps.presupuesto.services.auditoria import registrar_cambio  # noqa: E402

META = 10
ACTIVIDAD = 107
PROYECTO_BASURA = 2807
CODIGO = "2818"
SUBGRUPO_PAZ = 41


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--usuario", default=None)
    opts = ap.parse_args()

    with connection.cursor() as c:
        # El nombre NO se escribe a mano: se toma del espejo oficial.
        c.execute("""SELECT DISTINCT nombre_proyecto FROM sdp_meta_oficial
                     WHERE regexp_replace(codigo_proyecto, '^0+', '') = %s""", [CODIGO])
        fila = c.fetchone()
        if fila is None:
            sys.exit(f"El proyecto {CODIGO} no está en el espejo de SEGPLAN.")
        nombre = fila[0]

        c.execute("SELECT id FROM proyecto WHERE codigo = %s", [CODIGO])
        existente = c.fetchone()

        c.execute("""SELECT mp.id, mp.proyecto_id FROM meta_proyecto mp WHERE mp.meta_id = %s""",
                  [META])
        vinculo = c.fetchone()
        c.execute("SELECT proyecto_id FROM actividad_plan WHERE id = %s", [ACTIVIDAD])
        act = c.fetchone()

        print(f"  proyecto {CODIGO} «{nombre}» → "
              + (f"YA EXISTE (id {existente[0]})" if existente else "se va a crear"))
        print(f"  meta {META}: vínculo {vinculo[0] if vinculo else '?'} "
              f"apunta hoy al proyecto {vinculo[1] if vinculo else '?'}")
        print(f"  actividad {ACTIVIDAD}: apunta hoy al proyecto {act[0] if act else '?'}")

        if not opts.apply:
            print("\n(seco: nada se escribió. Agrega --apply --usuario <quien>.)")
            return

        if not opts.usuario:
            sys.exit("--apply exige --usuario: esto mueve datos del plan.")
        usuario = get_user_model().objects.filter(username=opts.usuario).first()
        if usuario is None:
            sys.exit(f"No existe el usuario «{opts.usuario}».")

        with transaction.atomic():
            if existente:
                pid = existente[0]
            else:
                # NI `id` NI `nombre_ci` se listan, y por motivos distintos:
                # `id` es IDENTITY GENERATED ALWAYS —pasarle un valor, aunque
                # salga de su propia secuencia, revienta con «cannot insert a
                # non-DEFAULT value»— y `nombre_ci` es una columna generada.
                c.execute("""INSERT INTO proyecto (codigo, nombre, subgrupo_id)
                             VALUES (%s, %s, %s)
                             RETURNING id""", [CODIGO, nombre, SUBGRUPO_PAZ])
                pid = c.fetchone()[0]
                registrar_cambio(
                    usuario=usuario, entidad="proyecto", entidad_id=pid,
                    campo="creacion", valor_anterior=None,
                    valor_nuevo=f"{CODIGO} · {nombre}",
                    proyecto_id=pid, subgrupo_id=SUBGRUPO_PAZ,
                    fuente=AuditoriaDato.SEGPLAN,
                    observacion=("El subgrupo Paz no tenía ningún proyecto: el suyo "
                                 "estaba mal escrito como «000007895». Nombre tomado "
                                 "del espejo oficial de SEGPLAN, no escrito a mano."))
                print(f"  ✓ proyecto creado: id {pid}")

            if vinculo and vinculo[1] != pid:
                c.execute("UPDATE meta_proyecto SET proyecto_id = %s WHERE id = %s",
                          [pid, vinculo[0]])
                registrar_cambio(
                    usuario=usuario, entidad="meta", entidad_id=META,
                    campo="proyecto", valor_anterior=str(vinculo[1]), valor_nuevo=str(pid),
                    proyecto_id=pid, subgrupo_id=SUBGRUPO_PAZ,
                    fuente=AuditoriaDato.MANUAL,
                    observacion=(f"Colgaba del proyecto {PROYECTO_BASURA}, cuyo código y "
                                 f"nombre eran ambos «000007895». Confirmado por Alex que "
                                 f"pertenece al {CODIGO}, el de Paz."))
                print(f"  ✓ meta {META} mudada al proyecto {pid}")

            if act and act[0] != pid:
                c.execute("UPDATE actividad_plan SET proyecto_id = %s WHERE id = %s",
                          [pid, ACTIVIDAD])
                registrar_cambio(
                    usuario=usuario, entidad="actividad_plan", entidad_id=ACTIVIDAD,
                    campo="proyecto", valor_anterior=str(act[0]), valor_nuevo=str(pid),
                    proyecto_id=pid, subgrupo_id=SUBGRUPO_PAZ,
                    fuente=AuditoriaDato.MANUAL,
                    observacion="Va con su meta: colgaba del mismo proyecto mal escrito.")
                print(f"  ✓ actividad {ACTIVIDAD} mudada al proyecto {pid}")

        c.execute("SELECT count(*) FROM meta_proyecto WHERE proyecto_id = %s", [PROYECTO_BASURA])
        m = c.fetchone()[0]
        c.execute("SELECT count(*) FROM actividad_plan WHERE proyecto_id = %s", [PROYECTO_BASURA])
        a = c.fetchone()[0]
        print(f"\n  el proyecto {PROYECTO_BASURA} queda con {m} metas y {a} actividades. "
              f"No se borra: borrarlo es decisión de Alex.")
        print(f"  Para deshacer: UPDATE meta_proyecto SET proyecto_id={PROYECTO_BASURA} "
              f"WHERE meta_id={META}; UPDATE actividad_plan SET proyecto_id={PROYECTO_BASURA} "
              f"WHERE id={ACTIVIDAD}; DELETE FROM proyecto WHERE codigo='{CODIGO}';")


if __name__ == "__main__":
    main()
