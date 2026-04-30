# Scripts SQL de la app `caracterizacion`

| Script | Aplicado | Descripción |
|---|---|---|
| `001_n12_setup.sql` | 2026-04-30 | Setup completo PR-N12-0: agrega `evento.sector_caracterizacion`, 5 secuencias BIGSERIAL, drop UNIQUE(persona_id), agrega `evento_id` a 3 tablas, `firma_mongo_id` en salud. |
| `001_n12_setup_rollback.sql` | — | Rollback del 001 (no usado). |

**Backup pre-PR-N12-0**: `~/Proyectos/postgres/backups/poblacion_kennedy_pre_n12_20260430_115315.dump`

**Verificación post-aplicación** (snapshot 2026-04-30 11:55):
- `evento.sector_caracterizacion` → existe
- 6 secuencias `caracterizacion_*_id_seq` → existen
- 0 constraints `UNIQUE(persona_id)` en caracterizacion_* → ok
- 6 tablas `caracterizacion_*` con `evento_id` → ok
- `caracterizacion_salud.firma_mongo_id` → existe
- `caracterizacion_cultura.persona_id` → NOT NULL
