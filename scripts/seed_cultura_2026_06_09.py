"""Seed Cultura — Fase 0 (fundación) + Fase 1-A (tipos) — 2026-06-09.

Aditivo (no borra data real). En transacción atómica.

FASE 0:
  - Fija nombre real del proyecto 2780 (estaba '2780').
  - Crea proyecto 2788 "KENNEDY IMPULSO CREATIVO" (Cultura).
  - Crea las 4 metas con cantidad como "Metas del proyecto"
    (Meta catálogo + MetaProyecto + Indicador con meta_magnitud):
      2780 M1: Capacitar 4000 personas
      2780 M2: Beneficiar 15 organizaciones
      2780 M3: Otorgar 38 estímulos
      2788 M1: Financiar 35 proyectos
  - Limpia 10 proyectos DEMO_* sueltos (sin hijos).

FASE 1-A:
  - Crea 3 tipo_evento nuevos: CULTURA_ORG, ESTIMULO_CULTURAL, PROYECTO_CULTURAL
    (requiere_actividad_plan=True para colgar de la cadena; formularios en Fase 1-B).

Idempotente: usa get_or_create; re-correrlo no duplica.
Backup de hoy 02:00 (<24h) disponible.

Ejecutar:  docker exec innova_k python scripts/seed_cultura_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection, transaction

SUBGRUPO_CULTURA = 1
DEP_INVERSION_LOCAL = 3

# (proyecto_id, nombre_meta, cantidad, unidad)
METAS = [
    (1,    "Capacitar personas en campos artísticos, culturales y patrimoniales", 4000, "personas"),
    (1,    "Beneficiar organizaciones artísticas, culturales y patrimoniales",      15, "organizaciones"),
    (1,    "Otorgar estímulos de apoyo al sector artístico y cultural",             38, "estímulos"),
    (2788, "Financiar proyectos del sector cultural y creativo",                    35, "proyectos"),
]

# (codigo, nombre, icono, color)
TIPOS = [
    ("CULTURA_ORG",       "Beneficio a organización cultural",     "fa-people-group", "#7E22CE"),
    ("ESTIMULO_CULTURAL", "Estímulo al sector artístico y cultural", "fa-award",        "#B45309"),
    ("PROYECTO_CULTURAL", "Proyecto cultural financiado",          "fa-lightbulb",    "#0D9488"),
]


def main():
    cur = connection.cursor()

    def ex(s, p=None):
        cur.execute(s, p or [])
        return cur.rowcount

    def q(s, p=None):
        cur.execute(s, p or [])
        return cur.fetchall()

    from apps.presupuesto.models.indicadores import MetaBD, MetaProyectoBD, Indicador

    with transaction.atomic():
        # ── FASE 0.1 — nombre real 2780 ──────────────────────────────
        n = ex("UPDATE proyecto SET nombre=%s WHERE id=1 AND codigo='2780'",
               ["KENNEDY PROYECTA TALENTO"])
        print(f"2780 nombre fijado: {n} fila")

        # ── FASE 0.2 — crear 2788 (proyecto.id sin secuencia) ────────
        existe = q("SELECT id FROM proyecto WHERE codigo='2788'")
        if not existe:
            ex("""INSERT INTO proyecto (id, codigo, nombre, subgrupo_id, dependencia_id)
                  OVERRIDING SYSTEM VALUE
                  VALUES (2788, '2788', %s, %s, %s)""",
               ["KENNEDY IMPULSO CREATIVO", SUBGRUPO_CULTURA, DEP_INVERSION_LOCAL])
            print("2788 creado (id=2788, Cultura)")
        else:
            print(f"2788 ya existe (id={existe[0][0]})")

        # ── FASE 0.3 — limpiar proyectos DEMO_ sueltos ───────────────
        demo_proys = [r[0] for r in q("SELECT id FROM proyecto WHERE codigo LIKE %s", ['DEMO%'])]
        if demo_proys:
            d = ex("DELETE FROM proyecto WHERE id = ANY(%s)", [demo_proys])
            print(f"proyectos DEMO_ borrados: {d}")

        # ── FASE 0.4 — metas con cantidad (Meta + MetaProyecto + Indicador) ──
        for proy_id, nombre, cantidad, unidad in METAS:
            meta, _ = MetaBD.objects.get_or_create(nombre=nombre)
            mp, _ = MetaProyectoBD.objects.get_or_create(meta_id=meta.codigo, proyecto_id=proy_id)
            ind, creado = Indicador.objects.get_or_create(
                meta_proyecto_id=mp.id, nombre=nombre,
                defaults=dict(unidad_medida=unidad, meta_magnitud=cantidad,
                              tipo_agregacion="SUMA", activo=True, descripcion=""),
            )
            print(f"  meta proy={proy_id} '{nombre[:45]}' objetivo={cantidad} {unidad} "
                  f"({'creada' if creado else 'ya existía'}) KPI id={ind.id}")

        # ── FASE 1-A — tipo_evento nuevos ────────────────────────────
        for codigo, nombre, icono, color in TIPOS:
            ya = q("SELECT codigo FROM tipo_evento WHERE codigo=%s", [codigo])
            if ya:
                print(f"  tipo_evento {codigo} ya existe")
                continue
            ex("""INSERT INTO tipo_evento
                  (codigo, nombre, descripcion, activo, icono, color, orden,
                   permite_inscripcion, permite_caracterizacion, permite_qr, requiere_actividad_plan)
                  VALUES (%s,%s,%s,true,%s,%s,50, false,false,true,true)""",
               [codigo, nombre, f"Captura de Cultura — {nombre}", icono, color])
            print(f"  tipo_evento {codigo} creado")

        print("COMMIT OK — seed Cultura aplicado.")


if __name__ == "__main__":
    main()
