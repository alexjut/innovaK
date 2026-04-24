"""
seed_demo_all.py — siembra demo robusta para dashboard ejecutivo.

Todo dentro de UNA transacción atómica. Si falla cualquier fase →
rollback automático, BD queda intacta.

Ejecución:
    docker exec innova_k python /app/apps/dashboard/scripts/seeds/seed_demo_all.py

Requisitos previos:
    - cleanup_demo.py ejecutado si hay data DEMO previa.
    - Backup BD (cron diario a las 02:00 cumple).

Esquemas verificados el 2026-04-23 (ver docs/PLAN_DEMO_SIEMBRA.md §3).
"""
import os
import random
import sys
from datetime import date, timedelta

import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402


random.seed(42)  # reproducible

# IDs base (todos >= 100000)
ID_BASE_PROYECTO = 100000
ID_BASE_META = 100000
ID_BASE_META_PROYECTO = 100000
ID_BASE_KPI = 100000
ID_BASE_EVENTO = 100000
ID_BASE_LUGAR_INC = 100000
ID_BASE_GEO = 100000
ID_BASE_AVANCE = 100000


# 10 proyectos inspirados en sectores Power BI Kennedy
PROYECTOS = [
    ("DEMO_ Fortalecimiento Institucional Kennedy", "Gobierno"),
    ("DEMO_ Malla Vial Kennedy 2026",               "Movilidad"),
    ("DEMO_ Educación Integral Kennedy",            "Educación"),
    ("DEMO_ Atención Primaria Comunitaria",         "Salud"),
    ("DEMO_ Deportes y Recreación Kennedy",         "Cultura"),
    ("DEMO_ Transferencias Monetarias Kennedy",     "Integración Social"),
    ("DEMO_ Apoyo al Emprendimiento Local",         "Desarrollo Económico"),
    ("DEMO_ Mujer con Derechos Kennedy",            "Mujer"),
    ("DEMO_ Buen Trato y Convivencia Kennedy",      "Buen Trato"),
    ("DEMO_ Ambiente y Sostenibilidad Kennedy",     "Ambiente"),
]

# 10 metas PDD con pct_objetivo (afecta qué tan llenos quedan los KPIs)
METAS_PDD = [
    ("DEMO_ Fortalecer capacidades institucionales", 0.85),
    ("DEMO_ Mejorar malla vial local",               0.45),
    ("DEMO_ Atención educativa integral",            0.70),
    ("DEMO_ Brigadas de salud comunitaria",          0.60),
    ("DEMO_ Promover actividad física y cultural",   0.90),
    ("DEMO_ Transferencias a familias vulnerables",  0.55),
    ("DEMO_ Impulso al emprendimiento local",        0.40),
    ("DEMO_ Empoderamiento de la mujer Kennedy",     0.30),
    ("DEMO_ Prevención de violencias",               0.75),
    ("DEMO_ Protección ambiental local",             0.25),
]

# KPIs por meta_idx (1-4 KPIs c/u, 35 total)
KPIS_POR_META = {
    0: [("Servidores capacitados", "personas", 500),
        ("Procesos optimizados",   "procesos", 25)],
    1: [("Metros cuadrados de vía intervenidos", "m2",  15000),
        ("Huecos reparados",                     "und", 1200),
        ("Obras entregadas",                     "und", 15)],
    2: [("Niños y jóvenes atendidos", "personas", 8000),
        ("Talleres dictados",         "und",      200)],
    3: [("Jornadas de salud",                 "und",      120),
        ("Personas atendidas en jornadas",    "personas", 5000),
        ("Vacunas aplicadas",                 "und",      2500)],
    4: [("Eventos culturales y deportivos", "und",      80),
        ("Asistentes a eventos",            "personas", 12000),
        ("Deportistas apoyados",            "personas", 400)],
    5: [("Bonos alimentarios entregados", "und",     1000),
        ("Familias beneficiadas",         "familias", 800),
        ("Subsidios económicos entregados","und",     600)],
    6: [("Emprendedores capacitados",           "personas", 200),
        ("Unidades productivas fortalecidas",   "und",      50),
        ("Capital semilla otorgado (millones)", "millones", 500)],
    7: [("Mujeres capacitadas en liderazgo",        "personas", 500),
        ("Talleres con enfoque de género",          "und",      100),
        ("Mujeres atendidas en casos de violencia", "personas", 300)],
    8: [("Jornadas de prevención",   "und",      80),
        ("Personas sensibilizadas",  "personas", 5000),
        ("Mediaciones realizadas",   "und",      150)],
    9: [("Árboles sembrados",                   "und", 2000),
        ("Puntos limpios instalados",           "und", 40),
        ("Toneladas de residuos recuperadas",   "ton", 500)],
}

# UPZ de Kennedy (codigo, nombre, lat centroide, lon centroide)
UPZS = [
    (45,  "Carvajal",        4.6200, -74.1650),
    (46,  "Castilla",        4.6400, -74.1500),
    (47,  "Kennedy Central", 4.6350, -74.1550),
    (48,  "Timiza",          4.6180, -74.1450),
    (78,  "Tintal Norte",    4.6450, -74.1800),
    (79,  "Calandaima",      4.6300, -74.1950),
    (80,  "Corabastos",      4.6520, -74.1720),
    (81,  "Gran Britalia",   4.6350, -74.1850),
    (82,  "Patio Bonito",    4.6280, -74.1780),
    (83,  "Las Margaritas",  4.6200, -74.1600),
    (113, "Bavaria",         4.6410, -74.1380),
    (44,  "Américas",        4.6460, -74.1200),
]

TIPOS_EVENTO = ["CAPACITACION", "CURSO", "ENTREGA", "INFO_TERRENO"]
DISTRIBUCION_TIPOS = (
    ["ENTREGA"] * 18
    + ["CAPACITACION"] * 15
    + ["CURSO"] * 12
    + ["INFO_TERRENO"] * 10
)  # 55 eventos


def _nombre_ci(nombre):
    """lowercase sin acentos (igual patrón que el proyecto)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", nombre)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def main():
    with transaction.atomic():
        with connection.cursor() as c:
            print("=" * 70)
            print("SIEMBRA DEMO — una sola transacción")
            print("=" * 70)

            # ─── Guardia: no sembrar si ya hay DEMO ──────────────────
            c.execute("SELECT COUNT(*) FROM proyecto WHERE id >= 100000")
            n_existentes = c.fetchone()[0]
            if n_existentes > 0:
                print(
                    f"\n⚠ Ya hay {n_existentes} proyectos DEMO (id>=100000). "
                    "Corre cleanup_demo.py primero."
                )
                raise SystemExit(1)

            # ─── Catálogos necesarios ───────────────────────────────
            c.execute("SELECT id FROM dependencia WHERE id = 3")
            dep_id = c.fetchone()[0]

            c.execute(
                "SELECT id FROM subgrupo WHERE dependencia_id = %s",
                [dep_id],
            )
            subgrupos = [r[0] for r in c.fetchall()]

            c.execute(
                "SELECT id FROM funcionario WHERE activo IS NOT FALSE "
                "ORDER BY id LIMIT 20"
            )
            funcionarios = [r[0] for r in c.fetchall()]

            # Un lugar_id válido para geo_referenciacion (NOT NULL)
            c.execute("SELECT id FROM lugar ORDER BY id LIMIT 1")
            lugar_generico_id = c.fetchone()[0]

            if not (subgrupos and funcionarios and lugar_generico_id):
                print("⚠ Faltan subgrupos/funcionarios/lugar para sembrar.")
                raise SystemExit(1)

            print(
                f"  catálogos: dep={dep_id}, subgrupos={len(subgrupos)}, "
                f"funcionarios={len(funcionarios)}, lugar_id={lugar_generico_id}"
            )

            # ═══════════════════════════════════════════════════════
            # FASE A — 10 proyectos
            # ═══════════════════════════════════════════════════════
            print("\n── Fase A: Proyectos ──")
            proyecto_ids = []
            for i, (nombre, sector) in enumerate(PROYECTOS):
                pid = ID_BASE_PROYECTO + i
                c.execute(
                    """
                    INSERT INTO proyecto (id, codigo, nombre, dependencia_id)
                    OVERRIDING SYSTEM VALUE
                    VALUES (%s, %s, %s, %s)
                    """,
                    [pid, f"DEMO{pid}", nombre, dep_id],
                )
                proyecto_ids.append(pid)
            print(f"  ✓ {len(proyecto_ids)} proyectos")

            # ═══════════════════════════════════════════════════════
            # FASE B — 10 metas PDD + 30 meta_proyecto
            # ═══════════════════════════════════════════════════════
            print("\n── Fase B: Metas PDD + meta_proyecto ──")
            meta_codigos = []
            for i, (nombre_meta, pct_obj) in enumerate(METAS_PDD):
                codigo = ID_BASE_META + i
                sector = PROYECTOS[i][1]
                # Nota: metas.proyecto_id tiene FK a tabla 'proyectos' (plural,
                # distinta de 'proyecto'). Dejamos NULL para evitar crear filas
                # en 'proyectos'. meta_proyecto.proyecto_id sí apunta a 'proyecto'.
                c.execute(
                    """
                    INSERT INTO metas (codigo, nombre, descripcion, sector)
                    OVERRIDING SYSTEM VALUE
                    VALUES (%s, %s, %s, %s)
                    """,
                    [codigo, nombre_meta, f"Meta PDD sector {sector}", sector],
                )
                meta_codigos.append(codigo)
            print(f"  ✓ {len(meta_codigos)} metas PDD")

            # 3 meta_proyecto por meta: cumplida, en curso, futura
            meta_proy_ids = []
            idx_mp = 0
            VENTANAS = [
                (date(2025, 1, 1), date(2025, 12, 31)),   # cumplida
                (date(2026, 1, 1), date(2026, 12, 31)),   # en curso
                (date(2026, 6, 1), date(2027, 12, 31)),   # futura
            ]
            for i, codigo_meta in enumerate(meta_codigos):
                for j, (fi, ff) in enumerate(VENTANAS):
                    mp_id = ID_BASE_META_PROYECTO + idx_mp
                    proy_id = proyecto_ids[(i + j) % len(proyecto_ids)]
                    c.execute(
                        """
                        INSERT INTO meta_proyecto
                            (id, meta_id, proyecto_id, fecha_inicio, fecha_fin)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [mp_id, codigo_meta, proy_id, fi, ff],
                    )
                    # guardamos (mp_id, meta_idx, ventana_idx) para decidir si
                    # se cuelga un KPI aquí
                    meta_proy_ids.append((mp_id, i, j))
                    idx_mp += 1
            print(f"  ✓ {len(meta_proy_ids)} meta_proyecto")

            # ═══════════════════════════════════════════════════════
            # FASE C — 35 KPIs. Cuelgan del meta_proyecto ventana 1 (en curso)
            # ═══════════════════════════════════════════════════════
            print("\n── Fase C: KPIs ──")
            kpis = []  # lista de dicts con datos para sembrar eventos y avances
            idx_kpi = 0
            for mp_id, meta_idx, ventana in meta_proy_ids:
                if ventana != 1:  # solo colgamos KPIs en meta_proyecto de 2026
                    continue
                pct_obj = METAS_PDD[meta_idx][1]
                for nombre_kpi, unidad, magnitud in KPIS_POR_META.get(meta_idx, []):
                    kpi_id = ID_BASE_KPI + idx_kpi
                    c.execute(
                        """
                        INSERT INTO presu_indicador_meta_proyecto
                            (id, meta_proyecto_id, nombre, descripcion,
                             unidad_medida, meta_magnitud, tipo_agregacion,
                             activo, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 'SUMA', TRUE,
                                NOW(), NOW())
                        """,
                        [kpi_id, mp_id, f"DEMO_ {nombre_kpi}",
                         f"KPI demo - {nombre_kpi}",
                         unidad, magnitud],
                    )
                    kpis.append({
                        "id": kpi_id,
                        "meta_idx": meta_idx,
                        "pct_obj": pct_obj,
                        "magnitud_meta": float(magnitud),
                        "unidad": unidad,
                        "nombre": nombre_kpi,
                    })
                    idx_kpi += 1
            print(f"  ✓ {len(kpis)} KPIs")

            # ═══════════════════════════════════════════════════════
            # FASE D — 55 eventos con geo + lugar_incidencia
            # ═══════════════════════════════════════════════════════
            print("\n── Fase D: Eventos + lugar_incidencia + geo ──")

            # Pre-asignación: cada evento → un KPI. Así podemos calcular
            # magnitudes coherentes para que cada KPI alcance su pct_obj.
            eventos_plan = []  # lista de (tipo, fecha, kpi_idx_en_lista)
            fecha_ini = date(2025, 10, 1)
            fecha_fin_rango = date(2026, 4, 20)
            dias_total = (fecha_fin_rango - fecha_ini).days

            for i in range(55):
                tipo = DISTRIBUCION_TIPOS[i]
                fecha_ev = fecha_ini + timedelta(
                    days=random.randint(0, dias_total)
                )
                kpi_idx = random.randrange(len(kpis))
                eventos_plan.append((tipo, fecha_ev, kpi_idx))

            # Contar eventos por KPI → calcular magnitud por evento
            eventos_por_kpi = [0] * len(kpis)
            for _, _, kidx in eventos_plan:
                eventos_por_kpi[kidx] += 1

            # Crear eventos e insertar cadena geo
            MAX_geo_actual = None
            MAX_lugar_inc_actual = None
            c.execute("SELECT COALESCE(MAX(id), 0) FROM geo_referenciacion")
            MAX_geo_actual = c.fetchone()[0]
            c.execute("SELECT COALESCE(MAX(id), 0) FROM lugar_incidencia")
            MAX_lugar_inc_actual = c.fetchone()[0]

            geo_next = max(MAX_geo_actual + 1, ID_BASE_GEO)
            lugar_inc_next = max(MAX_lugar_inc_actual + 1, ID_BASE_LUGAR_INC)

            evento_data = []  # (eid, kpi_id, magnitud, fecha)
            for i, (tipo, fecha_ev, kidx) in enumerate(eventos_plan):
                eid = ID_BASE_EVENTO + i
                kpi = kpis[kidx]

                # Magnitud: distribuir meta*pct_obj entre los eventos de este KPI
                aporte_total_kpi = kpi["magnitud_meta"] * kpi["pct_obj"]
                mag_base = aporte_total_kpi / max(1, eventos_por_kpi[kidx])
                # Variación ±40%
                magnitud = max(1, round(mag_base * (0.6 + random.random() * 0.8)))

                # UPZ con jitter
                cod_upz, nom_upz, lat_base, lon_base = random.choice(UPZS)
                lat = round(lat_base + (random.random() - 0.5) * 0.01, 6)
                lon = round(lon_base + (random.random() - 0.5) * 0.01, 6)

                # geo_referenciacion
                geo_id = geo_next
                geo_next += 1
                c.execute(
                    """
                    INSERT INTO geo_referenciacion
                        (id, lugar_id, latitud, longitud,
                         direccion_texto, fuente, precision)
                    VALUES (%s, %s, %s, %s, %s, 'demo', 'upz_centroide')
                    """,
                    [geo_id, lugar_generico_id, lat, lon,
                     f"DEMO_ {nom_upz} (siembra)"],
                )

                # lugar_incidencia (columna se llama 'geo_referenciacion')
                lugar_inc_id = lugar_inc_next
                lugar_inc_next += 1
                c.execute(
                    """
                    INSERT INTO lugar_incidencia (id, geo_referenciacion)
                    VALUES (%s, %s)
                    """,
                    [lugar_inc_id, geo_id],
                )

                # evento
                nombre_ev = (
                    f"DEMO_ {tipo.title()} en {nom_upz} "
                    f"({fecha_ev.strftime('%b %Y')})"
                )
                c.execute(
                    """
                    INSERT INTO evento (
                        id, nombre, tipo_evento_codigo,
                        fecha_inicio, fecha_fin, activo,
                        dependencia_id, subgrupo_id, funcionario_id,
                        indicador_id, magnitud_aportada,
                        lugar_incidencia_id, descripcion,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, TRUE,
                              %s, %s, %s,
                              %s, %s,
                              %s, %s,
                              NOW(), NOW())
                    """,
                    [eid, nombre_ev, tipo,
                     fecha_ev, fecha_ev,
                     dep_id, random.choice(subgrupos), random.choice(funcionarios),
                     kpi["id"], magnitud,
                     lugar_inc_id,
                     f"Evento demo {tipo} en UPZ {nom_upz}"],
                )

                evento_data.append((eid, kpi["id"], magnitud, fecha_ev))

            print(f"  ✓ {len(evento_data)} eventos + {len(evento_data)} geo "
                  f"+ {len(evento_data)} lugar_incidencia")

            # ═══════════════════════════════════════════════════════
            # FASE E — 55 avances (1 por evento, origen='EVENTO')
            # ═══════════════════════════════════════════════════════
            print("\n── Fase E: Avances ──")
            for i, (eid, kpi_id, magnitud, fecha_ev) in enumerate(evento_data):
                av_id = ID_BASE_AVANCE + i
                periodo = fecha_ev.strftime("%Y-%m")
                c.execute(
                    """
                    INSERT INTO presu_avance_ind_periodo (
                        id, indicador_id, evento_id, magnitud_aportada,
                        fecha_aporte, periodo, origen, activo,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'EVENTO', TRUE,
                              NOW(), NOW())
                    """,
                    [av_id, kpi_id, eid, magnitud, fecha_ev, periodo],
                )
            print(f"  ✓ {len(evento_data)} avances")

            # ═══════════════════════════════════════════════════════
            # REPORTE FINAL dentro de la tx (aún sin COMMIT)
            # ═══════════════════════════════════════════════════════
            print("\n" + "=" * 70)
            print("SIEMBRA EXITOSA — COMMIT inminente")
            print("=" * 70)
            print(f"  Proyectos:       {len(proyecto_ids)}")
            print(f"  Metas PDD:       {len(meta_codigos)}")
            print(f"  Meta-proyectos:  {len(meta_proy_ids)}")
            print(f"  KPIs:            {len(kpis)}")
            print(f"  Eventos:         {len(evento_data)}")
            print(f"  Avances:         {len(evento_data)}")

            # Stats de cumplimiento agregado
            c.execute(
                """
                SELECT imp.nombre, imp.meta_magnitud,
                       COALESCE(SUM(av.magnitud_aportada), 0) AS avance,
                       COUNT(av.id) AS n_avances
                FROM presu_indicador_meta_proyecto imp
                LEFT JOIN presu_avance_ind_periodo av
                       ON av.indicador_id = imp.id
                WHERE imp.id >= 100000
                GROUP BY imp.id, imp.nombre, imp.meta_magnitud
                ORDER BY (
                    COALESCE(SUM(av.magnitud_aportada), 0)::float
                    / NULLIF(imp.meta_magnitud, 0)
                ) DESC
                LIMIT 5
                """
            )
            print("\n  Top 5 KPIs por % cumplimiento:")
            for nombre, meta, avance, n in c.fetchall():
                pct = (float(avance) / float(meta) * 100) if meta else 0
                print(f"    {pct:6.1f}%  {nombre[:52]}")


if __name__ == "__main__":
    main()
