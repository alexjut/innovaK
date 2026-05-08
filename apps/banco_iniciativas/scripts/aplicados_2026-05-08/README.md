# Scripts SQL aplicados — sesión 2026-05-08 (Banco v2)

Aplicados sobre `poblacion_kennedy` durante la sesión de PR-2 y PR-3
del refactor v2 del Banco de Iniciativas Recreodeportivas.

| Script | PR | Descripción |
|---|---|---|
| `005_v2_pr2_soporte_legal.sql` | PR-2 | Refina catálogo `tipo_organizacion` (4 → 5 filas, "Otro" desactivado, +Aval deportivo). Agrega 2 columnas a `inscripcion_banco_iniciativa` (`numero_soporte_legal`, `soporte_legal_mongo_id`). |
| `006_v2_pr3_escenarios_actuales.sql` | PR-3 | Agrega `categoria_pot` al catálogo `escenario` + UPDATE filas existentes + INSERT 4 nuevas (Plazoleta, Humedal, Sendero, NTD). Crea tabla puente `inscripcion_banco_escenario_actual` (M2M para Sección 3 nueva, "uso actual"). |

Ambos scripts son idempotentes (`IF NOT EXISTS`, `ON CONFLICT DO UPDATE`)
y traen su propio bloque de reversa al final (comentado).

Backup pre-cambios: `~/Proyectos/postgres/backups/poblacion_kennedy_diario.dump` (02:00 AM).
