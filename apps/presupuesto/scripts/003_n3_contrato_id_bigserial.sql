-- =============================================================================
-- N3: id BIGSERIAL UNIQUE en contrato_proyecto y contrato_actividad
-- =============================================================================
-- Antes: ambas tablas tenían PK compuesta (contrato_id, X_id) sin `id` propio.
-- El modelo Django usaba `contrato = FK(primary_key=True)` como workaround,
-- lo que perdía silenciosamente filas cuando un contrato tenía >1 X
-- (bug latente: contrato_actividad ya tiene contrato_id=1 y =16 con 2 filas
-- cada uno; el ORM solo devolvía una).
--
-- Después: cada fila tiene `id BIGSERIAL UNIQUE NOT NULL`. La PK compuesta
-- original se preserva (no se reemplaza). El modelo Django puede usar `id`
-- como primary key sin perder filas.
--
-- Aplicado: 2026-05-11
-- Backup pre-cambio: poblacion_kennedy_pre_n3_<timestamp>.dump
-- Rollback: 003_n3_contrato_id_bigserial_rollback.sql
-- =============================================================================

BEGIN;

-- contrato_proyecto (96 filas en data actual, 1:1 efectivo)
ALTER TABLE contrato_proyecto ADD COLUMN id BIGSERIAL;
ALTER TABLE contrato_proyecto ADD CONSTRAINT contrato_proyecto_id_key UNIQUE (id);

-- contrato_actividad (98 filas, M:N real — 2 contratos con 2 actividades)
ALTER TABLE contrato_actividad ADD COLUMN id BIGSERIAL;
ALTER TABLE contrato_actividad ADD CONSTRAINT contrato_actividad_id_key UNIQUE (id);

COMMIT;
