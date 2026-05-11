-- Rollback de 004_n22_beneficiario_unique.sql
-- Solo correr si hay que revertir N22 (ej. si descubrimos que un flujo
-- legítimo necesita crear 2 Beneficiarios PERSONA para la misma persona).

DROP INDEX IF EXISTS idx_beneficiario_persona;
