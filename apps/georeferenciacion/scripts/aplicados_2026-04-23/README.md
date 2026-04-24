# Scripts aplicados — 2026-04-23

Scripts de schema y carga de datos **ya ejecutados** contra la BD
`poblacion_kennedy` como parte del refactor mapa-kennedy (Fase C4.3c/d/e).

## ⚠ No re-ejecutar sin pensar

Estos scripts son idempotentes en distinta medida:

| Script | Re-ejecutar es seguro? |
|---|---|
| `ddl_01_geometry_upz_barrio.sql` | ❌ — falla con "column already exists" |
| `ddl_02_create_parque.sql` | ❌ — falla con "relation already exists" |
| `ddl_03_create_escuela.sql` | ❌ — idem |
| `import_01_geometries.py` | ✓ — UPDATEs sobrescriben |
| `import_02_parques.py` | ✓ — INSERT ON CONFLICT DO NOTHING |
| `import_03_escuelas.py` | ✓ — dedup por (nombre, lat, lon). Pero ya no hay `escuelas_staging` para el backup, así que solo inserta faltantes. |

## Qué pasó el 2026-04-23

- **DDL 01**: `ALTER TABLE upz/barrio ADD COLUMN geometry JSONB`.
- **Import 01**: UPDATE a `upz.geometry` (12/12) y `barrio.geometry` (32/111).
  79 barrios quedan con geometry=NULL por mismatch de códigos IDECA vs BD
  (ver `docs/DEUDA_TECNICA.md §M22`).
- **DDL 02**: `CREATE TABLE parque` (12 cols, 3 índices, FK a upz/localidad).
- **Import 02**: 554 parques insertados (552 Kennedy), reproyectados
  EPSG:3857 → WGS84 con fórmula verificada.
- **DDL 03**: `CREATE TABLE escuela` (11 cols, 4 índices).
- **Import 03**: 241 escuelas (Cultura 86, Deporte 155) + backup SQL de
  `escuelas_staging` en `../../data/_backups/` + `DROP TABLE escuelas_staging`.

## Cómo usar estos scripts si un día hay que replicar el schema

En un entorno **limpio** (BD nueva, sin estas tablas):

```bash
# Ejecutar los DDL en orden
docker exec innova_k python manage.py shell < ddl_01_geometry_upz_barrio.sql
docker exec innova_k python manage.py shell < ddl_02_create_parque.sql
docker exec innova_k python manage.py shell < ddl_03_create_escuela.sql

# Ejecutar los imports
docker exec innova_k python /app/apps/georeferenciacion/scripts/aplicados_2026-04-23/import_01_geometries.py
docker exec innova_k python /app/apps/georeferenciacion/scripts/aplicados_2026-04-23/import_02_parques.py
docker exec innova_k python /app/apps/georeferenciacion/scripts/aplicados_2026-04-23/import_03_escuelas.py
```

## Rollback

Cada DDL tiene el rollback documentado en su cabecera. Resumen:

```sql
-- ddl_01
ALTER TABLE upz    DROP COLUMN geometry;
ALTER TABLE barrio DROP COLUMN geometry;

-- ddl_02
DROP TABLE parque;

-- ddl_03
DROP TABLE escuela;
-- Si se quiere restaurar escuelas_staging:
psql -f ../../data/_backups/escuelas_staging_2026-04-23_103845.sql
```

## Backups disponibles (fuera del repo)

- `~/Proyectos/postgres/backups/poblacion_kennedy_diario.dump` — diario
  automático a las 02:00.
- `~/Proyectos/postgres/backups/poblacion_kennedy_pre_c4_3_20260423_102810.dump`
  — snapshot tomado justo antes de ejecutar estos scripts (965 KB).
