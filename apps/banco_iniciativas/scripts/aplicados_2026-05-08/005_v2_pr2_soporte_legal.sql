-- ============================================================================
-- 005_v2_pr2_soporte_legal.sql
-- Banco de Iniciativas v2 — PR-2: refinar tipo_organizacion + soporte legal
-- ============================================================================
-- Fecha:    2026-05-08
-- Autor:    Claude + Alex
-- Backup:   poblacion_kennedy_diario.dump 02:00 AM del día (~/Proyectos/postgres/backups/)
-- Reversa:  ver al final del archivo (bloque comentado)
--
-- Cambios:
--   1. ALTER inscripcion_banco_iniciativa: agrega 2 columnas
--      (numero_soporte_legal TEXT, soporte_legal_mongo_id VARCHAR(64)).
--   2. Refina catálogo tipo_organizacion:
--      - UPDATE codigo 1 → "Club o escuela con Reconocimiento deportivo (IDRD)"
--      - UPDATE codigo 2 → "Persona jurídica con NIT (ESAL, fundación, asociación)"
--      - UPDATE codigo 3 → "Colectivo con carta de conformación"
--      - UPDATE codigo 4 → activo=false ("Otro" desactivado)
--      - INSERT codigo 5 → "Club con Aval deportivo (liga/federación)"
--      Reordena por contenido (Reconocimiento, Aval, NIT, Colectivo).
--
-- Compatibilidad:
--   - Las 4 inscripciones legacy referencian tipo_organizacion_codigo en
--     {1,2,3,4} y siguen apuntando al mismo registro renombrado.
--   - "Otro" (codigo=4) NO se borra; solo se desactiva. Las FK existentes
--     siguen válidas. El form filtra por activo=true.
--   - Las nuevas columnas son nullable → no rompen INSERTs antiguos.
-- ============================================================================

BEGIN;

-- ── 1. ALTER cabecera ──────────────────────────────────────────────────────
ALTER TABLE inscripcion_banco_iniciativa
  ADD COLUMN IF NOT EXISTS numero_soporte_legal TEXT NULL,
  ADD COLUMN IF NOT EXISTS soporte_legal_mongo_id VARCHAR(64) NULL;

COMMENT ON COLUMN inscripcion_banco_iniciativa.numero_soporte_legal IS
  'Número del documento que sustenta la existencia de la organización: '
  'resolución IDRD, número de aval deportivo, NIT, o referencia de la '
  'carta de conformación.';

COMMENT ON COLUMN inscripcion_banco_iniciativa.soporte_legal_mongo_id IS
  'ID del documento PDF cifrado en MongoDB (colección documentos). '
  'Mismo patrón que firma_mongo_id.';

-- ── 2. Refinar catálogo tipo_organizacion ──────────────────────────────────
-- Renombres (preserva codigos para no invalidar FKs existentes).
UPDATE tipo_organizacion
   SET nombre = 'Club o escuela con Reconocimiento deportivo (IDRD)',
       orden = 1
 WHERE codigo = 1;

UPDATE tipo_organizacion
   SET nombre = 'Persona jurídica con NIT (ESAL, fundación, asociación)',
       orden = 3
 WHERE codigo = 2;

UPDATE tipo_organizacion
   SET nombre = 'Colectivo con carta de conformación',
       orden = 4
 WHERE codigo = 3;

-- "Otro": desactivado (no se borra para preservar FKs históricas).
UPDATE tipo_organizacion
   SET activo = false
 WHERE codigo = 4;

-- Nueva opción: Aval deportivo (entre Reconocimiento y NIT por jerarquía).
-- OVERRIDING SYSTEM VALUE porque codigo es identity column GENERATED ALWAYS.
INSERT INTO tipo_organizacion (codigo, nombre, activo, orden)
OVERRIDING SYSTEM VALUE
VALUES (5, 'Club con Aval deportivo (liga/federación)', true, 2)
ON CONFLICT (codigo) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  activo = EXCLUDED.activo,
  orden  = EXCLUDED.orden;

-- Avanzar la secuencia interna del identity al menos al máximo usado para
-- evitar conflictos en futuros INSERTs sin OVERRIDING.
SELECT setval(
  pg_get_serial_sequence('tipo_organizacion', 'codigo'),
  GREATEST(5, (SELECT COALESCE(MAX(codigo), 0) FROM tipo_organizacion))
);

COMMIT;

-- ============================================================================
-- VERIFICACIÓN MANUAL POSTERIOR (correr después de aplicar)
-- ============================================================================
-- SELECT codigo, nombre, activo, orden FROM tipo_organizacion ORDER BY orden, codigo;
-- \d+ inscripcion_banco_iniciativa
-- (Las 2 columnas nuevas deben aparecer al final.)

-- ============================================================================
-- SCRIPT DE REVERSA (en caso de necesitar rollback manual)
-- ============================================================================
-- BEGIN;
-- ALTER TABLE inscripcion_banco_iniciativa
--   DROP COLUMN IF EXISTS numero_soporte_legal,
--   DROP COLUMN IF EXISTS soporte_legal_mongo_id;
-- DELETE FROM tipo_organizacion WHERE codigo = 5;
-- UPDATE tipo_organizacion SET activo = true WHERE codigo = 4;
-- UPDATE tipo_organizacion SET nombre = 'Club o Escuela con resolución IDRD vigente', orden = 1 WHERE codigo = 1;
-- UPDATE tipo_organizacion SET nombre = 'Organización', orden = 2 WHERE codigo = 2;
-- UPDATE tipo_organizacion SET nombre = 'Colectivo', orden = 3 WHERE codigo = 3;
-- COMMIT;
