"""Limpieza de datos demo/test/seed — 2026-06-09 (aprobado por Alex).

Borra eventos de prueba/demo/seed (SIN participantes reales) + el catálogo
presupuestal de prueba (metas/KPIs/meta_proyecto/avances/actividad_indicador).

PRESERVA explícitamente:
  - Banco de Iniciativas id=62 ("Prueba Piloto") y sus 24 inscripciones — ES REAL.
  - Los 28 eventos con 2.545 participantes reales (Novenas, etc.).
  - Los 4 "Recorrido" (ids 17,23,27,28).
  - Todas las personas (6.938) y beneficiarios.

Guardas defensivas:
  - Excluye id=62.
  - Excluye cualquier evento con filas en participante_evento.
  - Nulea FKs de filas que SE CONSERVAN antes de borrar padres.

Transacción atómica: o se borra todo coherente, o nada (rollback).
Idempotente: re-correrlo no borra de más (los sets quedan vacíos).

Backup previo verificado: poblacion_kennedy_diario.dump 2026-06-09 02:00 (<24h).

Ejecutar:
    docker exec innova_k python scripts/limpieza_demos_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection, transaction


def main():
    cur = connection.cursor()

    def q(s, p=None):
        cur.execute(s, p or [])
        return cur.fetchall()

    def ex(s, p=None):
        cur.execute(s, p or [])
        return cur.rowcount

    with transaction.atomic():
        # ── Conjuntos a borrar ───────────────────────────────────────
        delete_events = [r[0] for r in q(
            """SELECT id FROM evento e
               WHERE (nombre LIKE %s OR nombre ILIKE %s OR nombre ILIKE %s
                      OR id IN (51,52,53,54,55,56,57,58,59,60,100055))
                 AND id <> 62
                 AND NOT EXISTS (SELECT 1 FROM participante_evento pe
                                 WHERE pe.evento_id = e.id)""",
            ['DEMO_%', '%prueba%', '%test%'],
        )]
        demo_metas = [r[0] for r in q(
            "SELECT codigo FROM metas WHERE nombre ILIKE %s OR nombre ILIKE %s OR nombre ILIKE %s",
            ['%prueba%', '%test%', '%demo%'],
        )]
        demo_mp = [r[0] for r in q(
            "SELECT id FROM meta_proyecto WHERE meta_id = ANY(%s)", [demo_metas],
        )]
        demo_kpis = [r[0] for r in q(
            "SELECT id FROM presu_indicador_meta_proyecto "
            "WHERE meta_proyecto_id = ANY(%s) OR nombre ILIKE %s OR nombre ILIKE %s",
            [demo_mp, '%demo%', '%prueba%'],
        )]

        assert 62 not in delete_events, "ABORT: Banco id=62 quedó en el set de borrado"
        print(f"A borrar -> eventos:{len(delete_events)} metas:{len(demo_metas)} "
              f"meta_proyecto:{len(demo_mp)} KPIs:{len(demo_kpis)}")

        # ── Nulear FKs desde filas que SE CONSERVAN ──────────────────
        n1 = ex("UPDATE evento SET indicador_id=NULL "
                "WHERE indicador_id = ANY(%s) AND NOT (id = ANY(%s))",
                [demo_kpis, delete_events])
        n2 = ex("UPDATE contrato_actividad_plan SET meta_proyecto_id=NULL "
                "WHERE meta_proyecto_id = ANY(%s)", [demo_mp])
        print(f"FKs nuleados: evento.indicador_id={n1} contrato_act_plan.meta_proyecto_id={n2}")

        # ── Borrado de hijos ─────────────────────────────────────────
        a = ex("DELETE FROM presu_avance_ind_periodo "
               "WHERE evento_id = ANY(%s) OR indicador_id = ANY(%s)",
               [delete_events, demo_kpis])
        b = ex("DELETE FROM actividad_indicador WHERE indicador_id = ANY(%s)", [demo_kpis])
        c = ex("DELETE FROM documento_evento WHERE evento_id = ANY(%s)", [delete_events])
        d = ex("DELETE FROM evento_info_terreno WHERE evento_id = ANY(%s)", [delete_events])
        print(f"avances={a} actividad_indicador={b} documento_evento={c} info_terreno={d}")

        # ── Catálogo presupuesto ─────────────────────────────────────
        e = ex("DELETE FROM presu_indicador_meta_proyecto WHERE id = ANY(%s)", [demo_kpis])
        # Tabla legacy presu_indicador (también referencia meta_proyecto).
        leg = ex("DELETE FROM presu_indicador WHERE meta_proyecto_id = ANY(%s)", [demo_mp])
        print(f"presu_indicador (legacy) borrados={leg}")
        f = ex("DELETE FROM meta_proyecto WHERE id = ANY(%s)", [demo_mp])
        g = ex("DELETE FROM metas WHERE codigo = ANY(%s)", [demo_metas])
        print(f"KPIs={e} meta_proyecto={f} metas={g}")

        # ── Eventos ──────────────────────────────────────────────────
        h = ex("DELETE FROM evento WHERE id = ANY(%s)", [delete_events])
        print(f"eventos={h}")

        # ── tipo_evento TESTZZ si no se usa ──────────────────────────
        usado = q("SELECT count(*) FROM evento WHERE tipo_evento_codigo='TESTZZ'")[0][0]
        i = ex("DELETE FROM tipo_evento WHERE codigo='TESTZZ'") if usado == 0 else 0
        print(f"tipo_evento TESTZZ borrado={i} (usado={usado})")

        # ── Verificación de preservados ──────────────────────────────
        banco = q("SELECT count(*) FROM inscripcion_banco_iniciativa WHERE evento_id=62")[0][0]
        ev62 = q("SELECT count(*) FROM evento WHERE id=62")[0][0]
        parts = q("SELECT count(*) FROM participante_evento")[0][0]
        print(f"PRESERVADO -> Banco evento62={ev62} inscripciones={banco} | participantes={parts}")
        assert ev62 == 1 and banco == 24, "ABORT: el Banco se vio afectado"
        assert parts == 2545, "ABORT: se perdieron participantes reales"

        print("COMMIT OK — limpieza completada.")


if __name__ == "__main__":
    main()
