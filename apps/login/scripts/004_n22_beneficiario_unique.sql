-- =============================================================================
-- N22: UNIQUE INDEX parcial en beneficiario(persona_id) WHERE tipo='PERSONA'
-- =============================================================================
-- Race condition latente: 2 requests concurrentes desde
-- `banco_iniciativas/forms/inscripcion.py:466`, `caracterizacion/views/deporte.py:29`,
-- `caracterizacion/views/salud.py` y otros call sites de
-- `asegurar_beneficiario_persona()` pueden crear 2 filas de Beneficiario
-- tipo PERSONA para la misma persona_id. Hoy la idempotencia depende solo
-- de la lógica de aplicación (`filter().first()`).
--
-- Auditoría pre-cambio (2026-05-11): 0 duplicados existentes.
--   3580 Beneficiarios tipo PERSONA, 0 personas con >1 fila activa o total.
-- El INDEX se aplica directo sin necesidad de limpieza previa.
--
-- Por qué UNIQUE INDEX parcial y no constraint:
--   - El índice es UNIQUE solo cuando tipo='PERSONA' Y persona_id NOT NULL.
--   - Beneficiarios tipo ORGANIZACION/PROVEEDOR/etc. NO se ven afectados
--     (su persona_id es NULL y la condición WHERE los excluye).
--   - Permite ON CONFLICT DO NOTHING en futuras inserciones racing.
--
-- Aplicado: 2026-05-11
-- Backup pre-cambio: poblacion_kennedy_pre_n22_<timestamp>.dump
-- Rollback: 004_n22_beneficiario_unique_rollback.sql
-- =============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_beneficiario_persona
    ON beneficiario(persona_id)
 WHERE tipo = 'PERSONA' AND persona_id IS NOT NULL;
