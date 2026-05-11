-- =============================================================================
-- N27: limpieza de datos sucios (usuarios y subgrupos)
-- =============================================================================
-- Decisiones tomadas con Alex (2026-05-11):
--   1. Subgrupo id=3 'Prticipación' (typo) → 'Participación'.
--   2. Subgrupo id=5 'Seguridad' se merge a id=38 (1 func + 4 eventos
--      migrados). DELETE de id=5.
--   3. Usuario id=9 'Coordionador' (typo) → 'Coordinador'. Solo grupo
--      `Coordinador` (los otros 5: Admin, UsuarioGeneral, Docente, Lider,
--      LiderParticipacion se quitan). Vinculación a subgrupo Cultura
--      (id=1) se hace en script Python complementario (Persona +
--      Funcionario, requiere lógica ORM).
--
-- Aplicado: 2026-05-11
-- Backup pre-cambio: poblacion_kennedy_pre_n27_<timestamp>.dump
-- Rollback: 003_n27_limpieza_datos_rollback.sql
-- =============================================================================

BEGIN;

-- 1. Rename Prticipación → Participación
UPDATE subgrupo
   SET nombre = 'Participación'
 WHERE id = 3 AND nombre = 'Prticipación';

-- 2a. Migrar funcionarios de Seguridad id=5 → id=38
UPDATE funcionario SET subgrupo_id = 38 WHERE subgrupo_id = 5;

-- 2b. Migrar eventos de Seguridad id=5 → id=38
UPDATE evento SET subgrupo_id = 38 WHERE subgrupo_id = 5;

-- 2c. Eliminar subgrupo id=5 (solo si quedó vacío)
DELETE FROM subgrupo
 WHERE id = 5
   AND NOT EXISTS (SELECT 1 FROM funcionario WHERE subgrupo_id = 5)
   AND NOT EXISTS (SELECT 1 FROM evento      WHERE subgrupo_id = 5);

-- 3a. Renombrar username del usuario id=9
UPDATE usuario
   SET username = 'Coordinador'
 WHERE id = 9 AND username = 'Coordionador';

-- 3b. Quitar todos los grupos del usuario 9 EXCEPTO 'Coordinador'
DELETE FROM usuario_grupos
 WHERE usuario_id = 9
   AND group_id NOT IN (SELECT id FROM auth_group WHERE name = 'Coordinador');

COMMIT;
